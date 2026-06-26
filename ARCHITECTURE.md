# Applyr AI Job Application Platform - Architecture Overview

## Overview

Applyr is an AI-powered job application platform that automates the entire job search and application process. This document describes the new architecture that makes Applyr operate using a single source of truth.

## Core Architecture

### 1. Single Source of Truth

Everything in Applyr originates from the **Resume** and flows through the following pipeline:

```
Resume
→ Profile
→ Search Strategy
→ Job Discovery
→ Scoring
→ Tailoring
→ Recruiter Discovery
→ Email Generation
→ Application Tracking
```

### 2. Core Data Models

The architecture uses typed Pydantic models to ensure data consistency:

#### Resume
- Personal information (name, email, phone, LinkedIn, GitHub)
- Skills (technical, soft, languages)
- Experience (work history, projects, education)
- Certifications, roles, confidence score
- Section detection and validation

#### Profile
- Inferred roles from skills
- Preferred locations and seniority
- Keywords for search
- Target roles and locations
- Technical skills categorization

#### Job
- Company, role, location, URL
- Source and description
- Required skills and fit score
- Application status and metadata

#### Recruiter
- Contact information and confidence
- Source and discovery metadata

#### Email
- Drafted and sent emails
- Attachments and delivery status

#### Application
- Job application lifecycle
- State transitions (discovered → submitted → responded)

### 3. Core Services

#### Profile Service
- Creates profiles from resume data
- Infers roles and keywords
- Validates profile completeness

#### Company Service
- Extracts company names from job listings
- Validates company information
- Enriches company data

#### Event Bus
- Centralized event system
- Publishes and subscribes to events
- Tracks pipeline execution

#### Pipeline Orchestrator
- Coordinates the entire pipeline
- Manages job processing
- Handles errors and retries

### 4. API Layer

The API provides dedicated endpoints for all resources:

#### Profile Endpoints
- `GET /api/profile` - Get user profile
- `PUT /api/profile` - Update profile

#### Resume Endpoints
- `GET /api/resume` - Get resume status
- `POST /api/resume/upload` - Upload resume
- `GET /api/resume/parsed` - Get parsed resume data

#### Job Endpoints
- `GET /api/jobs` - Get jobs
- `GET /api/jobs/{id}` - Get job by ID
- `GET /api/jobs/{id}/match` - Get job match information

#### Application Endpoints
- `GET /api/applications` - Get applications

#### Recruiter Endpoints
- `GET /api/recruiters` - Get recruiters

#### Email Endpoints
- `GET /api/emails` - Get emails
- `GET /api/email/status` - Get email status
- `POST /api/email/test` - Send test email

#### Pipeline Endpoints
- `POST /api/run` - Run pipeline
- `GET /api/pipeline/logs/{run_id}` - Get pipeline logs

#### Analytics Endpoints
- `GET /api/analytics` - Get analytics

#### System Health Endpoints
- `GET /api/status` - Get system status
- `GET /api/health` - Get system health

#### Setup Endpoints
- `GET /api/setup/status` - Get setup status

#### Configuration Endpoints
- `GET /api/config` - Get configuration

### 5. Pipeline Flow

1. **Resume Upload** - User uploads resume
2. **Resume Parsing** - Resume is parsed using multi-engine extraction
3. **Profile Creation** - Profile is generated from resume data
4. **Search Strategy** - Search strategy is created from profile
5. **Job Discovery** - Jobs are discovered based on search strategy
6. **Job Processing** - Jobs are scored, tailored, and processed
7. **Recruiter Discovery** - Recruiters are discovered for jobs
8. **Email Generation** - Emails are generated and sent
9. **Application Tracking** - Applications are tracked through lifecycle

### 6. Key Features

#### Resume-First Approach
- Resume is the single source of truth
- All operations originate from resume data
- No job search without valid resume data

#### Event-Driven Architecture
- Every agent publishes events
- Services subscribe to events
- Mission Control tracks all events

#### Strong Typing
- All models use Pydantic for validation
- Type safety across all services
- Consistent data structures

#### Modular Design
- Each service has a single responsibility
- Easy to extend and maintain
- Independent components

#### Observability
- Event bus tracks all operations
- Pipeline execution is transparent
- System health monitoring

### 7. Technology Stack

#### Core
- Python 3.8+
- Pydantic for data validation
- Flask for API layer
- SQLite for database

#### AI/ML
- PyMuPDF for PDF extraction
- pdfplumber for table extraction
- pypdf for fallback PDF parsing
- Groq for LLM inference
- Gemini for backup LLM

#### Web Scraping
- Tavily for job search
- BeautifulSoup for HTML parsing
- Requests for HTTP operations

#### Email
- Resend for primary email delivery
- Gmail API for fallback
- EmailSender service for unified sending

#### Agents
- LangChain for agent orchestration
- LangGraph for workflow management
- CrewAI for multi-agent systems

### 8. Deployment

#### Local Development
```bash
# Setup the environment
python setup.py

# Run the API server
python api/__init__.py

# Upload a resume and run the pipeline
# via the web interface
```

#### Environment Variables
```env
# Required
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
RESEND_API_KEY=your_resend_api_key
FROM_EMAIL=your_email@example.com

# Optional
GEMINI_API_KEY=your_gemini_api_key
SCRAPINGBEE_API_KEY=your_scrapingbee_api_key
HUNTER_API_KEY=your_hunter_api_key
CLEARBIT_API_KEY=your_clearbit_api_key

# Configuration
DRY_RUN=true
AUTO_APPLY=false
MIN_FIT_SCORE=50
MAX_EMAILS_PER_RUN=10
MAX_APPLICATIONS_PER_DAY=20
```

### 9. Frontend Integration

The frontend (Next.js app) consumes the API endpoints:

- Dashboard shows KPIs and resume status
- Mission Control tracks pipeline events
- Jobs page displays discovered jobs
- Applications page tracks application lifecycle
- Resume Studio validates parsed data
- Email Center manages email delivery
- Analytics page shows platform statistics
- System Health page monitors services
- Settings page configures platform

### 10. Future Enhancements

#### Auto-Apply
- Automated job application submission
- Smart job selection based on fit score
- Resume tailoring for each job
- Email personalization

#### Advanced Features
- Multi-language support
- Integration with additional job boards
- Advanced matching algorithms
- Candidate ranking
- Interview scheduling
- Offer tracking

## Migration Guide

### From Old Architecture

The new architecture replaces the old monolithic design with a modular, event-driven approach. Key changes:

1. **Resume Parsing** - Multi-engine extraction replaces single-engine parsing
2. **Profile Generation** - Automatic profile creation from resume data
3. **Job Discovery** - Resume-driven search replaces generic searches
4. **Company Extraction** - Reliable company name extraction and validation
5. **Recruiter Discovery** - Unified recruiter discovery service
6. **Email Service** - Separate email generation and delivery
7. **Application Lifecycle** - Structured application states and transitions
8. **Event Bus** - Centralized event system for observability

### Migration Steps

1. Upload a resume using the Resume Studio page
2. The system will parse the resume and create a profile
3. Run the pipeline to discover jobs
4. Review applications in the Applications page
5. Use the new API endpoints for custom integrations

## Success Criteria

Applyr should become:

- **Resume-first** - Everything originates from resume data
- **Event-driven** - All operations are tracked and observable
- **Strongly typed** - All data is validated and consistent
- **Modular** - Each component has a single responsibility
- **Observable** - All operations are tracked and logged
- **Scalable** - Easy to extend and maintain
- **Transparent** - Full visibility into pipeline execution

The architecture supports:

- Reliable Resume Parsing
- Resume-Driven Search
- Job Normalization
- Recruiter Discovery
- Email Delivery
- Mission Control
- Analytics
- Future Auto-Apply

without requiring major rewrites.