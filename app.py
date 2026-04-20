from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv
import os

load_dotenv('.env')

db         = SQLAlchemy()
login_manager = LoginManager()
mail       = Mail()


def create_app():
    app = Flask(__name__)

    # ── Core config ────────────────────────────────────────────────────────
    app.config['SECRET_KEY']                  = os.getenv('SECRET_KEY', 'meetassist-dev-secret-2024')
    app.config['SQLALCHEMY_DATABASE_URI']     = 'sqlite:///meetassist.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH']          = 100 * 1024 * 1024   # 100 MB
    app.config['UPLOAD_FOLDER']               = os.path.join(os.path.dirname(__file__), 'uploads')

    # ── Mail config ────────────────────────────────────────────────────────
    app.config['MAIL_SERVER']         = os.getenv('MAIL_SERVER',   'smtp.gmail.com')
    app.config['MAIL_PORT']           = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS']        = os.getenv('MAIL_USE_TLS',  'True') == 'True'
    app.config['MAIL_USERNAME']       = os.getenv('MAIL_USERNAME',  '')
    app.config['MAIL_PASSWORD']       = os.getenv('MAIL_PASSWORD',  '')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', ''))

    # ── AssemblyAI ─────────────────────────────────────────────────────────
    app.config['ASSEMBLYAI_API_KEY']  = os.getenv('ASSEMBLYAI_API_KEY', '')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view    = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    from models.user    import User
    from models.meeting import Meeting
    from models.task    import Task

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes.auth     import auth_bp
    from routes.main     import main_bp
    from routes.meetings import meetings_bp
    from routes.tasks    import tasks_bp
    from routes.api      import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(meetings_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()
        _seed_demo_data(app, db, User, Meeting, Task)

    return app


def _seed_demo_data(app, db, User, Meeting, Task):
    from datetime import datetime, timedelta
    with app.app_context():
        if db.session.query(User).count() > 0:
            return

        users_data = [
            {'name': 'Alice Johnson', 'email': 'alice@meetassist.com', 'password': 'password123', 'role': 'admin'},
            {'name': 'Bob Smith',     'email': 'bob@meetassist.com',   'password': 'password123', 'role': 'member'},
            {'name': 'Carol White',   'email': 'carol@meetassist.com', 'password': 'password123', 'role': 'member'},
            {'name': 'David Lee',     'email': 'david@meetassist.com', 'password': 'password123', 'role': 'member'},
        ]
        users = []
        for ud in users_data:
            u = User(name=ud['name'], email=ud['email'], role=ud['role'])
            u.set_password(ud['password'])
            db.session.add(u)
            users.append(u)
        db.session.flush()

        sample_transcript = """Alice: Good morning everyone. Let's start our Q4 planning meeting.

Bob: I've reviewed the Q3 metrics. User acquisition was up 23% but retention dropped slightly.

Carol: Users are struggling with the setup wizard. I can redesign the onboarding flow by end of next week.

David: The API integration can ship by November 15th. The analytics dashboard will take 3 weeks — December 5th.

Bob: I'll launch the Q4 campaign on November 1st. Carol, I need landing page designs by October 28th.

Carol: I'll have the landing page designs ready by October 28th and update social media assets too.

Alice: I'll prepare the investor update presentation by November 10th.

Alice: David, please resolve the high-priority security issues by October 31st. It's non-negotiable.

David: Understood. I'll prioritize that immediately."""

        meeting1 = Meeting(
            title='Q4 Planning Meeting',
            description='Quarterly planning session covering product, marketing, and budget',
            transcript=sample_transcript,
            summary='The team held a productive Q4 planning meeting. Key decisions included prioritizing the analytics dashboard for enterprise clients (due Dec 5), launching Q4 marketing campaign on Nov 1, and resolving critical security audit findings by Oct 31.',
            key_points='- User acquisition up 23% in Q3 but retention dropped\n- Onboarding flow needs redesign\n- API integration scheduled for Nov 15\n- Analytics dashboard promised to enterprise clients\n- Q4 marketing campaign launch on Nov 1\n- Security audit findings must be resolved',
            decisions='1. Carol to redesign onboarding flow by end of next week\n2. David to ship API integration by November 15\n3. Analytics dashboard deadline set for December 5\n4. Bob to launch Q4 marketing campaign November 1\n5. Security issues must be resolved by October 31',
            date=datetime.now() - timedelta(days=3),
            created_by=users[0].id,
            status='processed'
        )
        db.session.add(meeting1)
        db.session.flush()

        tasks_data = [
            {'desc': 'Redesign onboarding flow to reduce user drop-off',   'user': users[2], 'deadline': datetime.now() + timedelta(days=7),  'status': 'pending'},
            {'desc': 'Complete API integration and deployment',             'user': users[3], 'deadline': datetime.now() + timedelta(days=14), 'status': 'in_progress'},
            {'desc': 'Build analytics dashboard for enterprise clients',    'user': users[3], 'deadline': datetime.now() + timedelta(days=35), 'status': 'pending'},
            {'desc': 'Launch Q4 marketing campaign',                        'user': users[1], 'deadline': datetime.now() + timedelta(days=5),  'status': 'completed'},
            {'desc': 'Create new landing page designs',                     'user': users[2], 'deadline': datetime.now() + timedelta(days=2),  'status': 'completed'},
            {'desc': 'Update social media assets for Q4',                   'user': users[2], 'deadline': datetime.now() + timedelta(days=10), 'status': 'pending'},
            {'desc': 'Prepare investor update presentation',                'user': users[0], 'deadline': datetime.now() + timedelta(days=18), 'status': 'in_progress'},
            {'desc': 'Resolve high-priority security audit findings',       'user': users[3], 'deadline': datetime.now() + timedelta(days=1),  'status': 'pending'},
            {'desc': 'Send meeting invites for November 20 review',         'user': users[1], 'deadline': datetime.now() + timedelta(days=1),  'status': 'completed'},
        ]
        for td in tasks_data:
            t = Task(
                description=td['desc'],
                assigned_to=td['user'].id,
                assigned_name=td['user'].name,
                assigned_email=td['user'].email,
                deadline=td['deadline'],
                status=td['status'],
                meeting_id=meeting1.id,
                created_by=users[0].id
            )
            db.session.add(t)

        db.session.commit()
        print("✅ Demo data seeded successfully!")


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
