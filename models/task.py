from app import db
from datetime import datetime


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_name = db.Column(db.String(100))
    assigned_email = db.Column(db.String(120))
    deadline = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    priority = db.Column(db.String(10), default='medium')  # low, medium, high
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text)

    def is_overdue(self):
        if self.deadline and self.status != 'completed':
            return datetime.utcnow() > self.deadline
        return False

    def deadline_display(self):
        if not self.deadline:
            return 'No deadline'
        return self.deadline.strftime('%b %d, %Y')

    def status_badge(self):
        badges = {
            'pending': ('Pending', '#FF6B6B', '🔴'),
            'in_progress': ('In Progress', '#FECA57', '🟡'),
            'completed': ('Completed', '#1DD1A1', '🟢'),
        }
        return badges.get(self.status, ('Unknown', '#ccc', '⚪'))

    def to_dict(self):
        badge = self.status_badge()
        return {
            'id': self.id,
            'description': self.description,
            'assigned_to': self.assigned_to,
            'assigned_name': self.assigned_name,
            'assigned_email': self.assigned_email,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'deadline_display': self.deadline_display(),
            'status': self.status,
            'status_label': badge[0],
            'status_color': badge[1],
            'priority': self.priority,
            'meeting_id': self.meeting_id,
            'meeting_title': self.meeting.title if self.meeting else None,
            'is_overdue': self.is_overdue(),
            'created_at': self.created_at.isoformat(),
            'notes': self.notes
        }
