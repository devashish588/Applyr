#!/usr/bin/env python3
"""
Applyr Setup Script - Initialize project on first run.
Tests Groq API, creates directories, initializes database.
"""
import os
import sys
import json
import sqlite3
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def check_dependencies():
    """Check if required packages are installed."""
    print("\n[*] Checking dependencies...")

    required = {
        'dotenv': 'python-dotenv',
        'flask': 'Flask',
        'requests': 'requests',
        'apscheduler': 'APScheduler',
        'langchain': 'langchain',
        'langchain_openai': 'langchain-openai',
        'langgraph': 'langgraph',
    }
    missing = []

    for module, package in required.items():
        try:
            __import__(module)
            print(f"  [OK] {package}")
        except ImportError:
            print(f"  [MISSING] {package}")
            missing.append(package)

    if missing:
        print(f"\n  WARNING: Missing packages: {', '.join(missing)}")
        print("  Run: pip install -r requirements.txt")
        return False

    return True


def test_groq_api():
    """Test Groq API connectivity."""
    print("\n[*] Testing Groq API...")

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        print("  [FAIL] GROQ_API_KEY not set in .env")
        return False

    try:
        from utils.llm_client import chat
        response = chat("Say 'OK' and nothing else.")
        print(f"  [OK] Groq API working (response: {response[:50]})")
        return True
    except Exception as e:
        print(f"  [FAIL] Groq API failed: {e}")
        return False


def create_directories():
    """Create all necessary directories."""
    print("\n[*] Creating directories...")

    dirs = [
        'logs',
        'db',
        'uploads',
        'resume/tailored',
        'resume/cover_letters',
        'autofill/screenshots',
        'email/templates',
        'ui/templates',
    ]

    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {dir_path}")


def initialize_database():
    """Create SQLite database and tables."""
    print("\n[*] Initializing database...")

    db_path = 'db/applications.db'
    schema_path = 'db/schema.sql'

    if not os.path.exists(schema_path):
        print(f"  [FAIL] Schema file not found: {schema_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print(f"  [OK] Database initialized: {db_path}")
        return True
    except Exception as e:
        print(f"  [FAIL] Database initialization failed: {e}")
        return False


def check_profile():
    """Check if profile.json exists and is valid."""
    print("\n[*] Checking profile...")

    if os.path.exists('profile.json'):
        try:
            with open('profile.json', 'r') as f:
                profile = json.load(f)
            required = ['personal', 'skills', 'job_preferences']
            if all(key in profile for key in required):
                name = profile.get('personal', {}).get('name', 'Unknown')
                print(f"  [OK] Profile found (name: {name})")
                return True
            else:
                print("  [WARN] Profile missing required sections")
        except json.JSONDecodeError:
            print("  [FAIL] Profile JSON is invalid")
    else:
        print("  [WARN] profile.json not found")

    return False


def check_env():
    """Check if .env exists with required keys."""
    print("\n[*] Checking environment configuration...")

    if os.path.exists('.env'):
        groq_key = os.getenv('GROQ_API_KEY', '')
        if groq_key and groq_key != 'gsk_xxxxxxxxxxxxx':
            print(f"  [OK] .env found with Groq API key")
            return True
        else:
            print("  [WARN] .env found but GROQ_API_KEY not configured")
    else:
        print("  [FAIL] .env not found")
        print("  -> Run: copy .env.example .env")

    return False


def main():
    """Run setup."""
    print("=" * 60)
    print("  Applyr Project Setup (Groq API)")
    print("=" * 60)

    all_good = True

    if not check_dependencies():
        all_good = False

    create_directories()

    if not initialize_database():
        all_good = False

    check_profile()

    env_ok = check_env()

    if env_ok:
        test_groq_api()

    print(f"\n{'='*60}")
    print("  SETUP COMPLETE!" if all_good else "  SETUP COMPLETE WITH WARNINGS")
    print(f"{'='*60}")

    print("\n  Quick Start:")
    print("  1. Edit profile.json with YOUR details")
    print("  2. Ensure .env has your GROQ_API_KEY")
    print("  3. Run dashboard:  python ui/app.py")
    print("     Open http://localhost:5000")
    print("  4. Run pipeline:   python pipeline/manual_trigger.py --run-now")
    print("  5. Run scheduler:  python pipeline/scheduler.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
