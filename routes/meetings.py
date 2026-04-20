import os
import re
from datetime import datetime, timedelta

from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from models.meeting import Meeting
from models.task    import Task
from models.user    import User
from utils.nlp      import analyze_meeting

meetings_bp = Blueprint('meetings', __name__, url_prefix='/meetings')

ALLOWED_AUDIO = {'mp3', 'mp4', 'wav', 'm4a', 'ogg', 'webm', 'flac'}


def _allowed_audio(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO


# ── List ──────────────────────────────────────────────────────────────────────
@meetings_bp.route('/')
@login_required
def list_meetings():
    meetings = Meeting.query.order_by(Meeting.date.desc()).all()
    return render_template('meetings/list.html', meetings=meetings)


# ── New meeting (transcript OR audio) ─────────────────────────────────────────
@meetings_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_meeting():
    users = User.query.all()

    # Check if Gemini Transcription is configured
    from utils.gemini_audio import is_configured as ai_configured
    audio_enabled = ai_configured()

    if request.method == 'POST':
        title        = request.form.get('title', '').strip()
        description  = request.form.get('description', '').strip()
        transcript   = request.form.get('transcript', '').strip()
        meeting_date = request.form.get('meeting_date', '')
        input_mode   = request.form.get('input_mode', 'text')   # 'text' or 'audio'
        notify_users = request.form.getlist('notify_users')      # list of user IDs

        if not title:
            flash('Meeting title is required.', 'error')
            return render_template('meetings/new.html', users=users, audio_enabled=audio_enabled)

        # ── Audio upload path ──────────────────────────────────────────────
        if input_mode == 'audio':
            audio_file = request.files.get('audio_file')
            if not audio_file or audio_file.filename == '':
                flash('Please upload an audio file.', 'error')
                return render_template('meetings/new.html', users=users, audio_enabled=audio_enabled)
            if not _allowed_audio(audio_file.filename):
                flash(f'Unsupported file type. Allowed: {", ".join(ALLOWED_AUDIO)}', 'error')
                return render_template('meetings/new.html', users=users, audio_enabled=audio_enabled)
            if not audio_enabled:
                flash('Gemini API key not configured. Please add it to your .env file.', 'error')
                return render_template('meetings/new.html', users=users, audio_enabled=audio_enabled)

            # Save file temporarily
            safe_name  = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(audio_file.filename)}"
            save_path  = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name)
            audio_file.save(save_path)

            try:
                from utils.gemini_audio import transcribe_audio_file
                result     = transcribe_audio_file(save_path)
                transcript = result['transcript']
                flash(f'Audio transcribed successfully! ({result["duration_minutes"]} min, {result["word_count"]} words)', 'success')
            except Exception as e:
                flash(f'Audio transcription failed: {e}', 'error')
                return render_template('meetings/new.html', users=users, audio_enabled=audio_enabled)
            finally:
                if os.path.exists(save_path):
                    os.remove(save_path)

        # ── Validate transcript ────────────────────────────────────────────
        if not transcript:
            flash('Meeting transcript is required.', 'error')
            return render_template('meetings/new.html', users=users, audio_enabled=audio_enabled)

        try:
            date = datetime.strptime(meeting_date, '%Y-%m-%dT%H:%M') if meeting_date else datetime.utcnow()
        except ValueError:
            date = datetime.utcnow()

        meeting = Meeting(
            title=title,
            description=description,
            transcript=transcript,
            date=date,
            created_by=current_user.id,
            status='processing'
        )
        db.session.add(meeting)
        db.session.flush()

        # ── NLP Analysis ───────────────────────────────────────────────────
        try:
            nlp_result          = analyze_meeting(transcript, users)
            meeting.summary     = nlp_result['summary']
            meeting.key_points  = nlp_result['key_points']
            meeting.decisions   = nlp_result['decisions']
            meeting.keywords    = nlp_result['keywords']
            meeting.status      = 'processed'
            extracted_tasks     = nlp_result.get('tasks', [])
            created_tasks       = _create_tasks_from_nlp(extracted_tasks, meeting, users)
        except Exception as e:
            meeting.status = 'failed'
            created_tasks  = []
            flash(f'AI analysis partially failed: {e}', 'warning')

        db.session.commit()

        # ── Email notifications ────────────────────────────────────────────
        _send_meeting_emails(meeting, notify_users, created_tasks)

        flash('Meeting added and analyzed successfully! 🎉', 'success')
        return redirect(url_for('meetings.view_meeting', meeting_id=meeting.id))

    return render_template('meetings/new.html', users=users, audio_enabled=audio_enabled)


# ── View meeting ──────────────────────────────────────────────────────────────
@meetings_bp.route('/<int:meeting_id>')
@login_required
def view_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    tasks   = Task.query.filter_by(meeting_id=meeting_id).all()
    users   = User.query.all()
    return render_template('meetings/view.html', meeting=meeting, tasks=tasks, users=users)


# ── Send summary email manually ───────────────────────────────────────────────
@meetings_bp.route('/<int:meeting_id>/send-summary', methods=['POST'])
@login_required
def send_summary(meeting_id):
    meeting    = Meeting.query.get_or_404(meeting_id)
    user_ids   = request.form.getlist('notify_users')
    valid_ids  = [int(i) for i in user_ids if str(i).isdigit()]
    recipients = User.query.filter(User.id.in_(valid_ids)).all() if valid_ids else User.query.all()

    sent = _do_send_summary(meeting, recipients)
    if sent > 0:
        flash(f'Meeting summary sent to {sent} member(s)! 📧', 'success')
    else:
        flash('No emails sent. Check your email configuration in .env', 'warning')
    return redirect(url_for('meetings.view_meeting', meeting_id=meeting_id))


# ── Absent member public view ─────────────────────────────────────────────────
@meetings_bp.route('/<int:meeting_id>/absent-view')
def absent_view(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    tasks   = Task.query.filter_by(meeting_id=meeting_id).all()
    return render_template('meetings/absent_view.html', meeting=meeting, tasks=tasks)


# ── Delete ────────────────────────────────────────────────────────────────────
@meetings_bp.route('/<int:meeting_id>/delete', methods=['POST'])
@login_required
def delete_meeting(meeting_id):
    if current_user.role != 'admin':
        flash('Only admins can delete meetings.', 'error')
        return redirect(url_for('meetings.list_meetings'))
    meeting = Meeting.query.get_or_404(meeting_id)
    db.session.delete(meeting)
    db.session.commit()
    flash('Meeting deleted.', 'info')
    return redirect(url_for('meetings.list_meetings'))


# ── Internal helpers ──────────────────────────────────────────────────────────

def _create_tasks_from_nlp(extracted_tasks, meeting, users):
    user_map       = {u.name.lower(): u for u in users}
    first_name_map = {u.name.split()[0].lower(): u for u in users}
    email_map      = {u.email.lower(): u for u in users}
    created        = []

    for et in extracted_tasks:
        assigned_user = None
        
        # Check by email first (from Gemini)
        assigned_email = (et.get('assigned_email') or '').lower().strip()
        if assigned_email and assigned_email in email_map:
            assigned_user = email_map[assigned_email]
        
        if not assigned_user:
            speaker = (et.get('assigned_name') or '').lower().strip()
            if speaker:
                assigned_user = (user_map.get(speaker)
                                 or first_name_map.get(speaker.split()[0] if speaker else ''))

        deadline = _parse_deadline_hint(et.get('deadline_hint'))
        task = Task(
            description=et['description'][:200],
            assigned_to=assigned_user.id    if assigned_user else None,
            assigned_name=assigned_user.name if assigned_user else et.get('assigned_name'),
            assigned_email=assigned_user.email if assigned_user else et.get('assigned_email'),
            deadline=deadline,
            status='pending',
            meeting_id=meeting.id,
            created_by=meeting.created_by
        )
        db.session.add(task)
        created.append(task)

    return created


def _send_meeting_emails(meeting, notify_user_ids, created_tasks):
    """Send task-assignment emails + optional meeting summary."""
    from utils.email_utils import send_task_assigned_email, send_meeting_summary_email

    # Per-task emails
    db.session.flush()
    for task in created_tasks:
        if task.assigned_email:
            send_task_assigned_email(task, assigned_by_name=current_user.name)

    # Meeting summary to selected users
    if notify_user_ids:
        valid_ids = [int(i) for i in notify_user_ids if str(i).isdigit()]
        if valid_ids:
            recipients = User.query.filter(User.id.in_(valid_ids)).all()
            _do_send_summary(meeting, recipients)


def _do_send_summary(meeting, recipients):
    from utils.email_utils import send_meeting_summary_email
    return send_meeting_summary_email(meeting, recipients)


def _parse_deadline_hint(hint: str):
    if not hint:
        return None
    hint = hint.lower().strip()
    now  = datetime.utcnow()

    if 'next week'   in hint: return now + timedelta(days=7)
    if 'end of week' in hint: return now + timedelta(days=5)
    if 'next month'  in hint: return now + timedelta(days=30)
    if 'tomorrow'    in hint: return now + timedelta(days=1)
    if 'today'       in hint: return now

    month_map = {m: i+1 for i, m in enumerate([
        'january','february','march','april','may','june',
        'july','august','september','october','november','december'
    ])}
    for name, num in month_map.items():
        if name in hint:
            dm = re.search(r'\d+', hint)
            if dm:
                try:
                    dt = datetime(now.year, num, int(dm.group()))
                    return dt if dt >= now else datetime(now.year + 1, num, int(dm.group()))
                except ValueError:
                    pass
    return None
