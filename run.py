#!/usr/bin/env python3
"""
MeetAssist - Quick Start Script
Installs dependencies and launches the app.
"""
import subprocess, sys, os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run(cmd, **kw):
    print(f"  → {cmd}")
    subprocess.run(cmd, shell=True, check=True, **kw)

print("\n🚀 MeetAssist — Starting up...\n")

run(f'"{sys.executable}" -m pip install flask flask-sqlalchemy flask-login flask-wtf flask-mail werkzeug wtforms python-dotenv sumy nltk google-genai pydantic --quiet')

print("\n✅ Dependencies installed.")
print("🌐 Starting Flask server at http://localhost:5000\n")
print("   Demo login: alice@meetassist.com / password123\n")

os.environ["FLASK_APP"] = "app.py"
os.environ["FLASK_ENV"] = "development"

from app import create_app
app = create_app()
app.run(debug=True, port=5000, host="0.0.0.0")
