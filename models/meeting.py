from app import db
from datetime import datetime


class Meeting(db.Model):
    __tablename__ = 'meetings'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    transcript = db.Column(db.Text)
    summary = db.Column(db.Text)
    key_points = db.Column(db.Text)
    decisions = db.Column(db.Text)
    keywords = db.Column(db.String(500))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    duration_minutes = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')  # pending, processing, processed, failed
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship('Task', backref='meeting', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'summary': self.summary,
            'key_points': self.key_points,
            'decisions': self.decisions,
            'keywords': self.keywords,
            'date': self.date.strftime('%B %d, %Y') if self.date else '',
            'status': self.status,
            'task_count': self.tasks.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def get_key_points_list(self):
        if not self.key_points:
            return []
        return [p.strip().lstrip('-• ') for p in self.key_points.split('\n') if p.strip()]

    def get_decisions_list(self):
        if not self.decisions:
            return []
        lines = []
        for line in self.decisions.split('\n'):
            line = line.strip()
            if line:
                import re
                line = re.sub(r'^\d+\.\s*', '', line)
                lines.append(line)
        return lines
