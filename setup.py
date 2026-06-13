#!/usr/bin/env python3
"""
Applyr Setup Script - Initialize project on first run
"""
import os
import sys
import json
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """Check if required packages are installed."""
    print("\n📦 Checking dependencies...")
    
    required = ['anthropic', 'flask', 'requests', 'apscheduler', 'playwright']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True


def create_directories():
    """Create all necessary directories."""
    print("\n📁 Creating directories...")
    
    dirs = [
        'logs',
        'db',
        'uploads/jd_pdfs',
        'uploads/jd_screenshots',
        'resume/tailored',
        'resume/cover_letters',
        'autofill/screenshots',
        'email/templates',
        'ui/templates'
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {dir_path}")


def initialize_database():
    """Create SQLite database and tables."""
    print("\n🗄️  Initializing database...")
    
    db_path = 'db/applications.db'
    schema_path = 'db/schema.sql'
    
    if not os.path.exists(schema_path):
        print(f"  ✗ Schema file not found: {schema_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print(f"  ✓ Database created: {db_path}")
        return True
    except Exception as e:
        print(f"  ✗ Database initialization failed: {e}")
        return False


def check_profile():
    """Check if profile.json exists."""
    print("\n👤 Checking profile...")
    
    profile_path = 'profile.json'
    
    if os.path.exists(profile_path):
        try:
            with open(profile_path, 'r') as f:
                profile = json.load(f)
            
            # Verify required fields
            required = ['personal', 'skills', 'job_preferences']
            if all(key in profile for key in required):
                print(f"  ✓ Profile found and valid")
                return True
            else:
                print(f"  ⚠️  Profile missing required sections")
        except json.JSONDecodeError:
            print(f"  ✗ Profile JSON is invalid")
    else:
        print(f"  ℹ️  Profile not found: {profile_path}")
    
    # Create template
    create_profile_template(profile_path)
    return False


def create_profile_template(profile_path):
    """Create template profile.json."""
    print("  Creating template profile...")
    
    template = {
        "personal": {
            "name": "Your Full Name",
            "email": "your.email@example.com",
            "phone": "+1-XXX-XXX-XXXX",
            "linkedin": "https://linkedin.com/in/yourprofile",
            "github": "https://github.com/yourprofile",
            "portfolio": "https://yourportfolio.com",
            "city": "Your City",
            "pincode": "123456"
        },
        "skills": {
            "languages": ["Python", "JavaScript", "SQL"],
            "frameworks": ["Django", "React", "FastAPI"],
            "tools": ["Git", "Docker", "AWS"],
            "years_experience": 5,
            "certifications": []
        },
        "job_preferences": {
            "target_roles": ["Software Engineer", "Full Stack Developer"],
            "target_locations": ["Remote", "San Francisco", "New York"],
            "min_salary": 100000,
            "remote_ok": True,
            "fulltime_only": True,
            "interested_industries": ["Tech", "Finance"]
        },
        "experience_summary": "Senior software engineer with 5+ years building scalable systems",
        "key_achievements": [
            "Led migration of monolith to microservices, reducing latency by 40%",
            "Architected real-time data pipeline processing 1M+ events daily",
            "Mentored team of 3 junior engineers"
        ]
    }
    
    with open(profile_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"  ✓ Template created: {profile_path}")
    print("  ⚠️  UPDATE THIS FILE with your actual details!")


def check_env():
    """Check if .env exists."""
    print("\n🔑 Checking environment configuration...")
    
    if os.path.exists('.env'):
        print("  ✓ .env file found")
        return True
    else:
        print("  ℹ️  .env file not found")
        if os.path.exists('.env.example'):
            print("  → Run: cp .env.example .env")
            print("  → Then edit .env with your API keys")
        return False


def main():
    """Run setup."""
    print("=" * 60)
    print("🚀 Applyr Project Setup")
    print("=" * 60)
    
    all_good = True
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        all_good = False
    
    # Create directories
    create_directories()
    
    # Initialize database
    if not initialize_database():
        all_good = False
    
    # Check profile
    profile_valid = check_profile()
    
    # Check environment
    env_valid = check_env()
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ SETUP COMPLETE!" if all_good else "⚠️  SETUP COMPLETE WITH WARNINGS")
    print("=" * 60)
    
    print("\n📋 Next Steps:")
    print("  1. Edit profile.json with your details")
    print("  2. Copy .env.example to .env and fill in API keys")
    print("  3. Add your master resume: resume/master_resume.pdf")
    print("  4. Add your agents to agents/ folder")
    print("  5. Run: python pipeline/scheduler.py (for auto scheduling)")
    print("     or:  python ui/app.py (for web dashboard)")
    
    print("\n📖 Documentation: See README.md for detailed instructions")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
