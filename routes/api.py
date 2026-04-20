from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models.user    import User
from models.meeting import Meeting
from models.task    import Task
from app import db
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/tasks/<int:task_id>/status', methods=['PATCH'])
@login_required
def update_task_status(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404

    # Role check: admin can update any task, member only their own
    if current_user.role != 'admin' and task.assigned_to != current_user.id:
        return jsonify({'error': 'Permission denied. You can only update your own tasks.'}), 403

    data       = request.get_json() or {}
    new_status = data.get('status')

    if new_status not in ('pending', 'in_progress', 'completed'):
        return jsonify({'error': 'Invalid status value'}), 400

    task.status       = new_status
    task.completed_at = datetime.utcnow() if new_status == 'completed' else None
    db.session.commit()

    return jsonify({'success': True, 'task': task.to_dict()})


@api_bp.route('/tasks', methods=['GET'])
@login_required
def get_tasks():
    status  = request.args.get('status')
    user_id = request.args.get('user_id')
    search  = request.args.get('search', '')

    query = Task.query
    if status:  query = query.filter_by(status=status)
    if user_id: query = query.filter_by(assigned_to=int(user_id))
    if search:  query = query.filter(Task.description.ilike(f'%{search}%'))

    tasks = query.order_by(Task.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tasks])


@api_bp.route('/users', methods=['GET'])
@login_required
def get_users():
    return jsonify([u.to_dict() for u in User.query.all()])


@api_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    all_tasks = Task.query.all()
    total     = len(all_tasks)
    completed = sum(1 for t in all_tasks if t.status == 'completed')
    pending   = sum(1 for t in all_tasks if t.status == 'pending')
    in_prog   = sum(1 for t in all_tasks if t.status == 'in_progress')

    return jsonify({
        'total_tasks':     total,
        'completed':       completed,
        'pending':         pending,
        'in_progress':     in_prog,
        'completion_rate': round((completed / total * 100) if total else 0, 1),
        'total_meetings':  Meeting.query.count(),
        'total_users':     User.query.count(),
    })


@api_bp.route('/meetings/<int:meeting_id>/tasks', methods=['GET'])
@login_required
def meeting_tasks(meeting_id):
    tasks = Task.query.filter_by(meeting_id=meeting_id).all()
    return jsonify([t.to_dict() for t in tasks])


@api_bp.route('/me/tasks', methods=['GET'])
@login_required
def my_tasks():
    """Get tasks assigned to the current user."""
    tasks = Task.query.filter_by(assigned_to=current_user.id).all()
    return jsonify([t.to_dict() for t in tasks])
