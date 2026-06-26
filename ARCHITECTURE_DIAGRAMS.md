# Resume Parser Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     RESUME PARSER v2.1 (PRODUCTION)                    │
└─────────────────────────────────────────────────────────────────────────┘

                              USER UPLOADS RESUME
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │  Level 1: Text Extraction        │
                    │  (Multi-Engine with Fallback)    │
                    └────────────┬─────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
         ┌─────────┐        ┌──────────┐      ┌────────┐
         │ PyMuPDF │        │pdfplumber│      │  OCR   │
         │(Digital)│        │ (Tables) │      │(Scanned)
         └────┬────┘        └────┬─────┘      └───┬────┘
              │                  │                 │
              └──────────────────┼────────────────┘
                                 │
                    ✓ Text extracted (raw)
                    ✓ Engine used logged
                    ✓ Char count & pages tracked
                                 │
                                 ▼
                    ┌──────────────────────────────────┐
                    │  Level 2: Section Detection      │
                    │  (Regex + Heading Matching)      │
                    └────────────┬─────────────────────┘
                                 │
                    ✓ Sections found & merged
                    ✓ Missing sections identified
                                 │
                                 ▼
                    ┌──────────────────────────────────┐
                    │  Level 3: LLM Structuring        │
                    │  (Extract Structured Fields)     │
                    └────────────┬─────────────────────┘
                                 │
                    ✓ Contact info (regex fast path)
                    ✓ Skills extracted & categorized
                    ✓ Experience structured
                    ✓ Education parsed
                    ✓ Projects extracted
                    ✓ Fallback: regex-based extraction
                                 │
                                 ▼
                    ┌──────────────────────────────────┐
                    │  Level 4: Validation & Scoring   │
                    │  (Confidence: 0-100 points)      │
                    └────────────┬─────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼ Scoring Logic         │                       ▼
         
    Name         = 15 pts        │               Calculate overall
    Email        = 10 pts        │               confidence score
    Skills (5+)  = 20 pts        │               (total weighted)
    Experience   = 20 pts        │
    Education    = 15 pts        │
    Projects (2+)= 20 pts        │
    ────────────────────         │
    MAX          = 100 pts       │
                                 │
         ┌───────────────────────┴───────────────────────┐
         │                                               │
         ▼                                               ▼
    
    CONFIDENCE SCORE          MISSING CRITICAL FIELDS?
    ├─ < 70% ?  ──┐           ├─ No name?       ──┐
    ├─ > 90%? ✅ │           ├─ No skills?     ──┤
    └─────────────┘           ├─ No experience? ──┤
                              ├─ No projects?   ──┤
                              └────────────────────┘
                                     │
                                     ▼
                    ┌──────────────────────────────────┐
                    │    BLOCKING DECISION LOGIC       │
                    └────────────┬─────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
         YES (Block)                           NO (Continue)
         Resume Blocked                        ▼ Resume Valid
              │                    ┌──────────────────────────────┐
              │                    │  Level 5: Role Inference     │
              │                    │  (Skill to Role Mapping)     │
              │                    └──────────┬───────────────────┘
              │                               │
              │                    ✓ Inferred 3-5 likely roles
              │                               │
              │                               ▼
              │                    ┌──────────────────────────────┐
              │                    │  Level 6: Resume Assembly    │
              │                    │  (Assemble Final JSON)       │
              │                    └──────────┬───────────────────┘
              │                               │
              │                    ✓ Resume object created
              │                    ✓ Confidence & evidence tracked
              │                    ✓ Parse log attached
              │                               │
              │                               ▼
              │                    ┌──────────────────────────────┐
              │                    │   Save Resume Cache          │
              │                    │  (resume_cache.json)         │
              │                    └──────────┬───────────────────┘
              │                               │
              │                    ✓ Cache file written
              │                    ✓ Skills categorized
              │                    ✓ Stats stored
              │                               │
              │                               ▼
              │                    ┌──────────────────────────────┐
              │                    │   Orchestrator Check         │
              │                    │   (run_full_pipeline)        │
              │                    └──────────┬───────────────────┘
              │                               │
              │                    ✅ Resume Valid → Continue Pipeline
              │                               │
              │                               ▼
              │                    ┌──────────────────────────────┐
              │                    │   FULL PIPELINE RUNS         │
              │                    │  (Discover→Parse→Score→     │
              │                    │   Tailor→Email→Send)         │
              │                    └──────────────────────────────┘
              │
              └─────────────────────────────────────────────────────┐
                                                                    │
                                 ┌──────────────────────────────────┘
                                 │
                  ┌──────────────┴───────────────────┐
                  │                                  │
         APP Sends SSE Event                Frontend Displays
         "step": "blocked"                  ResumeBlockedCard
         "validation": {                    ├─ ✓/✗ Name
         "name": false,                     ├─ ✓/✗ Skills
         "skills": false,                   ├─ ✓/✗ Experience
         "experience": true,                ├─ ✓/✗ Education
         "education": true,                 ├─ ✓/✗ Projects
         "projects": false,                 ├─ Confidence: 62%
         "confidence": 62                   └─ Upload Button
         }
```

## Data Flow: Resume Cache

```
┌───────────────────────────────────────────────────────────┐
│         Resume Parsed & Cached Successfully               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         resume_cache/resume_cache.json
         {
           "name": "John Doe",
           "email": "john@example.com",
           "skills": [
             "Python", "React", "AWS", ...
           ],
           "skills_categorized": {
             "languages": ["Python"],
             "frameworks": ["React"],
             "cloud": ["AWS"],
             ...
           },
           "experience": [
             {
               "company": "Tech Corp",
               "role": "Senior Engineer",
               "start_date": "2020",
               "technologies_used": ["Python", "AWS"],
               ...
             }
           ],
           "projects": [
             {
               "name": "AI Chat",
               "tech_stack": ["Python", "LangChain"],
               "github": "...",
               "deployment": "..."
             }
           ],
           "education": [...],
           "target_roles": [
             "Backend Engineer",
             "Full Stack Developer"
           ],
           "confidence": 85,
           "extraction_stats": {
             "engine_used": "PyMuPDF",
             "chars_extracted": 12543,
             "pages": 2
           }
         }
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    
    Job Matching  Role Inference  Email Generation
    (no re-parse) (from skills)   (from cache)
    
    ✅ All downstream components read from cache
    ✅ No re-parsing needed
    ✅ Consistent data across pipeline
```

## Component Dependencies

```
Frontend (React/Next.js)
    └── API Client
        └── Flask App (ui/app.py)
            └── Orchestrator (pipeline/orchestrator.py)
                ├── Resume Parser Agent
                │   ├── Multi-Engine Extraction
                │   ├── Section Detection
                │   ├── LLM Structuring
                │   ├── Confidence Scoring
                │   ├── Role Inference
                │   └── Cache Storage
                │
                ├── Job Application Agent
                ├── Email Drafting Agent
                ├── Recruiter Discovery Agent
                └── Web Research Agent

Resume Cache (JSON)
    ↓ (consumed by)
    - Job Scorer
    - Tailor Agent
    - Email Generator
    - Role Inference
    - Database Storage
```

## Blocking Decision Tree

```
                          Resume Uploaded
                                │
                                ▼
                    Parse Resume → Get Confidence
                                │
                    ┌───────────┴───────────┐
                    │                       │
               Confidence > 70?         Has Critical Fields?
                    │ YES                  │
                    └─────┬────────────────┘
                          │ YES
                          ▼
                ┌─────────────────────┐
                │  ✅ CONTINUE        │
                │  Pipeline Runs      │
                │  Jobs Discovered    │
                │  Emails Drafted     │
                └─────────────────────┘
                
                          │
                          │ NO to either
                          │
                          ▼
                ┌─────────────────────┐
                │  🛑 BLOCKED         │
                │  Show Error Card    │
                │  User Uploads New   │
                │  Resume            │
                └─────────────────────┘
```

