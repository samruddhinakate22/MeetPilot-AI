"""
Email notification utilities for MeetAssist.
All sends are wrapped in try/except so a missing mail config
never crashes the app — it just prints a warning.
"""
from flask import current_app, render_template_string
from flask_mail import Message


def _mail():
    from app import mail
    return mail


TASK_ASSIGNED_TEMPLATE = """
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
    <div style="background:#6C63FF;padding:28px 32px;">
      <h1 style="color:#fff;margin:0;font-size:22px;">📌 New Task Assigned</h1>
    </div>
    <div style="padding:28px 32px;">
      <p style="color:#333;font-size:16px;">Hi <strong>{{ assignee_name }}</strong>,</p>
      <p style="color:#555;">A new task has been assigned to you{% if meeting_title %} from the meeting <strong>{{ meeting_title }}</strong>{% endif %}:</p>

      <div style="background:#f8f7ff;border-left:4px solid #6C63FF;border-radius:6px;padding:16px 20px;margin:20px 0;">
        <p style="font-size:16px;font-weight:bold;color:#333;margin:0 0 8px;">{{ task_description }}</p>
        {% if deadline %}
        <p style="color:#888;margin:4px 0;font-size:13px;">📅 Deadline: <strong style="color:#FF6B6B;">{{ deadline }}</strong></p>
        {% endif %}
        <p style="color:#888;margin:4px 0;font-size:13px;">🔴 Status: <strong>Pending</strong></p>
        <p style="color:#888;margin:4px 0;font-size:13px;">⚡ Priority: <strong>{{ priority }}</strong></p>
      </div>

      {% if assigned_by %}
      <p style="color:#555;font-size:14px;">Assigned by: <strong>{{ assigned_by }}</strong></p>
      {% endif %}

      <p style="color:#555;font-size:14px;">Please log in to MeetAssist to update your task status.</p>

      <div style="margin-top:28px;padding-top:20px;border-top:1px solid #eee;">
        <p style="color:#aaa;font-size:12px;margin:0;">MeetAssist — AI Meeting Intelligence</p>
      </div>
    </div>
  </div>
</body>
</html>
"""

MEETING_SUMMARY_TEMPLATE = """
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
    <div style="background:#1DD1A1;padding:28px 32px;">
      <h1 style="color:#fff;margin:0;font-size:22px;">🎙️ Meeting Summary</h1>
      <p style="color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:14px;">{{ meeting_date }}</p>
    </div>
    <div style="padding:28px 32px;">
      <h2 style="color:#333;font-size:20px;margin:0 0 16px;">{{ meeting_title }}</h2>

      {% if summary %}
      <div style="background:#f8f8f8;border-radius:6px;padding:16px;margin-bottom:20px;">
        <h3 style="color:#555;font-size:13px;text-transform:uppercase;letter-spacing:1px;margin:0 0 8px;">📝 Summary</h3>
        <p style="color:#333;font-size:14px;line-height:1.7;margin:0;">{{ summary }}</p>
      </div>
      {% endif %}

      {% if key_points %}
      <div style="margin-bottom:20px;">
        <h3 style="color:#555;font-size:13px;text-transform:uppercase;letter-spacing:1px;margin:0 0 10px;">💡 Key Points</h3>
        {% for point in key_points %}
        <div style="display:flex;margin-bottom:6px;">
          <span style="color:#6C63FF;margin-right:8px;">◆</span>
          <span style="color:#444;font-size:14px;">{{ point }}</span>
        </div>
        {% endfor %}
      </div>
      {% endif %}

      {% if tasks %}
      <div style="margin-bottom:20px;">
        <h3 style="color:#555;font-size:13px;text-transform:uppercase;letter-spacing:1px;margin:0 0 10px;">📌 Your Tasks</h3>
        {% for task in tasks %}
        <div style="background:#fff8f8;border:1px solid #FFE0E0;border-radius:6px;padding:12px 16px;margin-bottom:8px;">
          <p style="color:#333;font-weight:bold;margin:0 0 4px;font-size:14px;">{{ task.description }}</p>
          {% if task.deadline_display() != 'No deadline' %}
          <p style="color:#FF6B6B;font-size:12px;margin:0;">📅 Due: {{ task.deadline_display() }}</p>
          {% endif %}
        </div>
        {% endfor %}
      </div>
      {% endif %}

      <div style="margin-top:28px;padding-top:20px;border-top:1px solid #eee;">
        <p style="color:#aaa;font-size:12px;margin:0;">MeetAssist — AI Meeting Intelligence</p>
      </div>
    </div>
  </div>
</body>
</html>
"""


def send_task_assigned_email(task, assigned_by_name=None):
    """Send email to the person a task was assigned to."""
    if not task.assigned_email:
        return False

    if not current_app.config.get('MAIL_USERNAME'):
        print(f"⚠️  Email not configured — skipping task assignment email to {task.assigned_email}")
        return False

    try:
        html = render_template_string(
            TASK_ASSIGNED_TEMPLATE,
            assignee_name=task.assigned_name or 'Team Member',
            task_description=task.description,
            deadline=task.deadline_display() if task.deadline else None,
            priority=task.priority.capitalize(),
            meeting_title=task.meeting.title if task.meeting else None,
            assigned_by=assigned_by_name,
        )
        msg = Message(
            subject=f'📌 New Task Assigned: {task.description[:50]}',
            recipients=[task.assigned_email],
            html=html
        )
        _mail().send(msg)
        print(f"✅ Task email sent to {task.assigned_email}")
        return True
    except Exception as e:
        print(f"⚠️  Failed to send task email: {e}")
        return False


def send_meeting_summary_email(meeting, recipients):
    """
    Send meeting summary + tasks to a list of User objects or email strings.
    recipients: list of User objects
    """
    if not current_app.config.get('MAIL_USERNAME'):
        print("⚠️  Email not configured — skipping meeting summary email")
        return 0

    sent = 0
    for user in recipients:
        email = user.email if hasattr(user, 'email') else user
        name  = user.name  if hasattr(user, 'name')  else email

        # Get tasks assigned to this user for this meeting
        from models.task import Task
        user_tasks = []
        if hasattr(user, 'id'):
            user_tasks = Task.query.filter_by(
                meeting_id=meeting.id,
                assigned_to=user.id
            ).all()

        try:
            html = render_template_string(
                MEETING_SUMMARY_TEMPLATE,
                meeting_title=meeting.title,
                meeting_date=meeting.date.strftime('%B %d, %Y') if meeting.date else '',
                summary=meeting.summary,
                key_points=meeting.get_key_points_list()[:5],
                tasks=user_tasks,
            )
            msg = Message(
                subject=f'🎙️ Meeting Summary: {meeting.title}',
                recipients=[email],
                html=html
            )
            _mail().send(msg)
            sent += 1
            print(f"✅ Meeting summary sent to {email}")
        except Exception as e:
            print(f"⚠️  Failed to send summary to {email}: {e}")

    return sent
