from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models.user import User
from models.meeting import Meeting
from models.task import Task
from app import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    users = User.query.all()
    meetings = Meeting.query.order_by(Meeting.date.desc()).all()
    all_tasks = Task.query.all()

    total_tasks = len(all_tasks)
    completed_tasks = sum(1 for t in all_tasks if t.status == 'completed')
    pending_tasks = sum(1 for t in all_tasks if t.status == 'pending')
    in_progress_tasks = sum(1 for t in all_tasks if t.status == 'in_progress')

    my_tasks = Task.query.filter_by(assigned_to=current_user.id).all()

    stats = {
        'total_tasks': total_tasks,
        'completed': completed_tasks,
        'pending': pending_tasks,
        'in_progress': in_progress_tasks,
        'total_meetings': len(meetings),
        'total_users': len(users),
        'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
        'my_tasks': len(my_tasks),
        'my_completed': sum(1 for t in my_tasks if t.status == 'completed'),
    }

    return render_template('dashboard.html',
                           users=users,
                           meetings=meetings,
                           all_tasks=all_tasks,
                           stats=stats,
                           my_tasks=my_tasks)
