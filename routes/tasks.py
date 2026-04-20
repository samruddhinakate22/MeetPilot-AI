from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.task    import Task
from models.user    import User
from models.meeting import Meeting
from app import db
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


def _can_edit(task):
    """Admin can edit any task. Member can only edit tasks assigned to them."""
    return current_user.role == 'admin' or task.assigned_to == current_user.id


def _can_delete(task):
    """Only admins can delete tasks."""
    return current_user.role == 'admin'


# ── List ──────────────────────────────────────────────────────────────────────
@tasks_bp.route('/')
@login_required
def list_tasks():
    status_filter = request.args.get('status', '')
    user_filter   = request.args.get('user', '')
    search        = request.args.get('search', '')

    query = Task.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if user_filter and str(user_filter).isdigit():
        query = query.filter_by(assigned_to=int(user_filter))
    if search:
        query = query.filter(Task.description.ilike(f'%{search}%'))

    tasks    = query.order_by(Task.created_at.desc()).all()
    users    = User.query.all()
    meetings = Meeting.query.all()

    return render_template('tasks/list.html', tasks=tasks, users=users,
                           meetings=meetings, status_filter=status_filter,
                           user_filter=user_filter, search=search)


# ── New task (admin only) ─────────────────────────────────────────────────────
@tasks_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_task():
    users    = User.query.all()
    meetings = Meeting.query.order_by(Meeting.date.desc()).all()

    if request.method == 'POST':
        description  = request.form.get('description', '').strip()
        assigned_to  = request.form.get('assigned_to', '')
        deadline_str = request.form.get('deadline', '')
        priority     = request.form.get('priority', 'medium')
        meeting_id   = request.form.get('meeting_id', '')
        notes        = request.form.get('notes', '').strip()
        send_email   = request.form.get('send_email') == 'on'

        if not description:
            flash('Task description is required.', 'error')
            return render_template('tasks/new.html', users=users, meetings=meetings)

        assigned_user = None
        if assigned_to:
            assigned_user = db.session.get(User, int(assigned_to))

        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError:
                pass

        task = Task(
            description=description,
            assigned_to=assigned_user.id    if assigned_user else None,
            assigned_name=assigned_user.name if assigned_user else None,
            assigned_email=assigned_user.email if assigned_user else None,
            deadline=deadline,
            priority=priority,
            meeting_id=int(meeting_id) if meeting_id else None,
            notes=notes,
            created_by=current_user.id
        )
        db.session.add(task)
        db.session.commit()

        # Send email notification if requested
        if send_email and task.assigned_email:
            from utils.email_utils import send_task_assigned_email
            sent = send_task_assigned_email(task, assigned_by_name=current_user.name)
            if sent:
                flash(f'Task created and email sent to {task.assigned_name}! 📧', 'success')
            else:
                flash('Task created. Email could not be sent (check .env config).', 'warning')
        else:
            flash('Task created successfully!', 'success')

        return redirect(url_for('tasks.list_tasks'))

    return render_template('tasks/new.html', users=users, meetings=meetings)


# ── Update status (AJAX) ──────────────────────────────────────────────────────
@tasks_bp.route('/<int:task_id>/update-status', methods=['POST'])
@login_required
def update_status(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        if request.is_json:
            return jsonify({'error': 'Task not found'}), 404
        flash('Task not found.', 'error')
        return redirect(request.referrer or url_for('tasks.list_tasks'))

    if not _can_edit(task):
        if request.is_json:
            return jsonify({'error': 'Permission denied'}), 403
        flash('You can only update tasks assigned to you.', 'error')
        return redirect(request.referrer or url_for('tasks.list_tasks'))

    # Support both JSON (AJAX) and form POST
    if request.is_json:
        new_status = (request.get_json() or {}).get('status', task.status)
    else:
        new_status = request.form.get('status', task.status)

    if new_status not in ('pending', 'in_progress', 'completed'):
        if request.is_json:
            return jsonify({'error': 'Invalid status'}), 400
        flash('Invalid status.', 'error')
        return redirect(request.referrer or url_for('tasks.list_tasks'))

    task.status       = new_status
    task.completed_at = datetime.utcnow() if new_status == 'completed' else None
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'task': task.to_dict()})

    flash(f'Task status updated to {new_status.replace("_"," ")}.', 'success')
    return redirect(request.referrer or url_for('tasks.list_tasks'))


# ── Delete (admin only) ───────────────────────────────────────────────────────
@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        flash('Task not found.', 'error')
        return redirect(request.referrer or url_for('tasks.list_tasks'))

    if not _can_delete(task):
        flash('Only admins can delete tasks.', 'error')
        return redirect(request.referrer or url_for('tasks.list_tasks'))

    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'info')
    return redirect(request.referrer or url_for('tasks.list_tasks'))
