#!/usr/bin/env python3
"""
Setup script for Applyr AI job application platform.

This script initializes the new architecture with the core models,
services, and API layer.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.models import Resume, Profile, Job, Recruiter, Email, Application, PipelineRun, SearchStrategy, Company, PipelineEvent, SystemHealth
from core.services import get_profile_service, get_company_service, get_event_bus, get_orchestrator
from api import app


def setup_database():
    """Setup the database with the new schema."""
    print("Setting up database...")
    
    from db.db_client import get_db
    db = get_db()
    
    # The database schema is already set up in db_client.py
    # We just need to ensure it has all the necessary columns
    print("Database setup complete.")


def setup_environment():
    """Setup environment variables."""
    print("Setting up environment...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("Warning: .env file not found. Please create it with required environment variables.")
    else:
        print("Environment variables loaded from .env file.")


def setup_services():
    """Setup core services."""
    print("Setting up core services...")
    
    # Initialize services
    profile_service = get_profile_service()
    company_service = get_company_service()
    event_bus = get_event_bus()
    orchestrator = get_orchestrator()
    
    print(f"Profile service initialized: {profile_service}")
    print(f"Company service initialized: {company_service}")
    print(f"Event bus initialized: {event_bus}")
    print(f"Orchestrator initialized: {orchestrator}")
    
    print("Core services setup complete.")


def setup_api():
    """Setup API layer."""
    print("Setting up API layer...")
    
    # The API is already initialized in api/__init__.py
    print("API layer setup complete.")


def main():
    """Main setup function."""
    print("=" * 60)
    print("Applyr AI Job Application Platform - Setup")
    print("=" * 60)
    
    try:
        setup_environment()
        setup_database()
        setup_services()
        setup_api()
        
        print("=" * 60)
        print("Setup complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Upload a resume using the Resume Studio page")
        print("2. Run the pipeline to discover jobs")
        print("3. Review applications in the Applications page")
        print("\nAPI endpoints:")
        print("- GET /api/profile - Get user profile")
        print("- GET /api/resume - Get resume status")
        print("- POST /api/resume/upload - Upload resume")
        print("- GET /api/jobs - Get jobs")
        print("- POST /api/run - Run pipeline")
        print("- GET /api/analytics - Get analytics")
        print("- GET /api/status - Get system status")
        
    except Exception as e:
        print(f"\nError during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()