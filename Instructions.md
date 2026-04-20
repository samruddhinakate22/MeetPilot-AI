# 🎙️ MeetAssist — AI Meeting Intelligence

A full-stack meeting assistant web application that automatically summarizes meetings, extracts tasks, assigns them to team members, and tracks progress — all in a sleek, modern dashboard.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ installed
- pip package manager

### 1. Install & Run (One Command)
```bash
cd meetassist
python run.py
```

Or manually:
```bash
# Install dependencies
pip install -r requirements.txt

# Start the app
python app.py
```

Then open: **http://localhost:5000**

---

## 🔑 Demo Login Credentials

| Name | Email | Password | Role |
|------|-------|----------|------|
| Alice Johnson | alice@meetassist.com | password123 | admin |
| Bob Smith | bob@meetassist.com | password123 | member |
| Carol White | carol@meetassist.com | password123 | member |
| David Lee | david@meetassist.com | password123 | member |

---

## 📁 Project Structure

```
meetassist/
│
├── app.py                  # Flask app factory + demo data seeding
├── run.py                  # Quick-start launcher script
├── requirements.txt        # Python dependencies
│
├── models/
│   ├── __init__.py
│   ├── user.py             # User model (auth, avatars, stats)
│   ├── meeting.py          # Meeting model (transcript, summary, etc.)
│   └── task.py             # Task model (status, deadline, assignee)
│
├── routes/
│   ├── __init__.py
│   ├── auth.py             # Login / signup / logout
│   ├── main.py             # Dashboard route
│   ├── meetings.py         # Meeting CRUD + NLP processing
│   ├── tasks.py            # Task CRUD + status updates
│   └── api.py              # REST API endpoints (AJAX)
│
├── utils/
│   ├── __init__.py
│   └── nlp.py              # NLP engine (summarization, NER, task extraction)
│
├── templates/
│   ├── base.html           # Sidebar layout, flash messages, topbar
│   ├── dashboard.html      # Main dashboard with stats + team overview
│   ├── auth/
│   │   ├── login.html
│   │   └── signup.html
│   ├── meetings/
│   │   ├── list.html       # All meetings grid
│   │   ├── new.html        # Upload/paste transcript form
│   │   ├── view.html       # Meeting detail: summary, tasks, transcript tabs
│   │   └── absent_view.html # Public share page for absent members
│   └── tasks/
│       ├── list.html       # Filterable task table
│       └── new.html        # Manual task creation form
│
├── static/
│   ├── css/main.css        # Full design system (dark theme)
│   └── js/main.js          # AJAX status updates, animations, UI
│
└── instance/
    └── meetassist.db       # SQLite database (auto-created)
```

---

## 🗄️ Database Schema

### `users`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto ID |
| name | VARCHAR(100) | Full name |
| email | VARCHAR(120) UNIQUE | Login email |
| password_hash | VARCHAR(255) | Bcrypt hash |
| role | VARCHAR(20) | admin / member |
| created_at | DATETIME | Registration time |

### `meetings`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto ID |
| title | VARCHAR(200) | Meeting name |
| description | TEXT | Optional description |
| transcript | TEXT | Full meeting text |
| summary | TEXT | AI-generated summary |
| key_points | TEXT | Bullet-point highlights |
| decisions | TEXT | Numbered decisions |
| keywords | VARCHAR(500) | Comma-separated keywords |
| date | DATETIME | When meeting occurred |
| status | VARCHAR(20) | pending/processing/processed/failed |
| created_by | FK → users.id | Who added this meeting |

### `tasks`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto ID |
| description | TEXT | What needs to be done |
| assigned_to | FK → users.id | Linked user account |
| assigned_name | VARCHAR(100) | Name (even if no account) |
| assigned_email | VARCHAR(120) | Email |
| deadline | DATETIME | Optional due date |
| status | VARCHAR(20) | pending/in_progress/completed |
| priority | VARCHAR(10) | low/medium/high |
| meeting_id | FK → meetings.id | Source meeting |
| created_by | FK → users.id | Creator |
| completed_at | DATETIME | When marked done |
| notes | TEXT | Extra context |

---

## 🤖 AI / NLP Features

The NLP engine (`utils/nlp.py`) uses **pure Python** — no heavy models required:

### Summarization
- TF-IDF-like sentence scoring
- Position weighting (first/last sentences matter more)
- Length normalization

### Task Extraction
- Regex-based action verb detection (`will send`, `I'll prepare`, `please complete`, etc.)
- Speaker-to-user matching (name matching from transcript → users table)
- Deadline hint parsing (`by Friday`, `November 15`, `next week`)

### Keyword Extraction
- Stop word filtering
- Term frequency + position boosting
- Returns top N keywords

### Named Entity Recognition
- Pattern-based speaker detection (`Name: message` format)
- Name capitalization heuristics

---

## 🌐 REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks` | List tasks (filter: status, user_id, search) |
| PATCH | `/api/tasks/<id>/status` | Update task status (AJAX) |
| GET | `/api/users` | List all users with stats |
| GET | `/api/stats` | Global task/meeting counts |
| GET | `/api/meetings/<id>/tasks` | Tasks for a meeting |

### PATCH `/api/tasks/<id>/status` example:
```json
// Request
{ "status": "completed" }

// Response
{ "success": true, "task": { "id": 1, "status": "completed", ... } }
```

---

## 🎯 Key Features

### 1. Meeting Upload & AI Analysis
- Paste any meeting transcript
- AI automatically extracts summary, key points, decisions, tasks, keywords
- Speaker-aware task assignment

### 2. Dashboard
- Live stats: total/completed/pending/in-progress tasks
- Team member cards with completion progress bars
- Recent meetings and task table
- Real-time status updates via AJAX (no page reload)

### 3. Task Management
- Filter by status / user / keyword search
- Update status inline (dropdown + checkbox)
- Priority levels (low/medium/high)
- Overdue detection (highlighted in red)

### 4. Absent Member View
- Shareable public URL: `/meetings/<id>/absent-view`
- No login required
- Shows summary, key points, decisions, and all tasks

### 5. Authentication
- Bcrypt password hashing
- Flask-Login session management
- Remember me support

---

## 📝 Sample Transcript Format

For best AI extraction results, use this format:
```
Alice: Good morning everyone. Let's discuss the Q4 roadmap.

Bob: I've reviewed the metrics. User retention dropped 5%. 
  I'll prepare a full report by Friday.

Carol: I'll redesign the onboarding flow by end of next week.
  That should address the drop-off.

Alice: Agreed. Bob, please send the report to all stakeholders
  before the board meeting on November 15th.

David: I'll resolve the security audit issues by October 31st.
  This is critical before launch.
```

---

## ⚙️ Configuration

Set these in a `.env` file or environment variables:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///meetassist.db
FLASK_ENV=development
```

---

## 🔧 Extending the App

### Add Email Notifications
```python
# Install: pip install Flask-Mail
from flask_mail import Mail, Message
mail = Mail(app)
```

### Add Real Speech-to-Text
```python
# Install: pip install openai-whisper
import whisper
model = whisper.load_model("base")
result = model.transcribe("meeting.mp3")
transcript = result["text"]
```

### Upgrade NLP with Transformers
```python
# Install: pip install transformers torch
from transformers import pipeline
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
```

---

## 🐛 Troubleshooting

**Port already in use:**
```bash
python app.py --port 5001
```

**Database issues:**
```bash
rm instance/meetassist.db  # Reset database
python app.py               # Recreates with demo data
```

**Import errors:**
```bash
pip install -r requirements.txt --upgrade
```
