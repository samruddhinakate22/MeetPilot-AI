from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='member')  # admin, member
    avatar_color = db.Column(db.String(10), default='#6C63FF')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    tasks = db.relationship('Task', foreign_keys='Task.assigned_to', backref='assignee', lazy='dynamic')
    created_meetings = db.relationship('Meeting', foreign_keys='Meeting.created_by', backref='creator', lazy='dynamic')

    AVATAR_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57',
                     '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43']

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_avatar_initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return parts[0][0].upper() + parts[1][0].upper()
        return self.name[:2].upper()

    def get_avatar_color(self):
        idx = self.id % len(self.AVATAR_COLORS)
        return self.AVATAR_COLORS[idx]

    def task_stats(self):
        from app import db
        from models.task import Task
        from sqlalchemy import func
        total     = db.session.query(Task).filter_by(assigned_to=self.id).count()
        completed = db.session.query(Task).filter_by(assigned_to=self.id, status='completed').count()
        pending   = db.session.query(Task).filter_by(assigned_to=self.id, status='pending').count()
        in_progress = db.session.query(Task).filter_by(assigned_to=self.id, status='in_progress').count()
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'in_progress': in_progress,
            'completion_rate': round((completed / total * 100) if total > 0 else 0, 1)
        }

    def to_dict(self):
        stats = self.task_stats()
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'initials': self.get_avatar_initials(),
            'avatar_color': self.get_avatar_color(),
            'task_stats': stats,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
