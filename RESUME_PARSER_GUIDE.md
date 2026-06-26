# Resume Parser Quick Reference

## Quick Start

### Enable the Production Parser
The production-grade parser is **now enabled by default** in all components.

### Dependencies Required
```bash
# Core extraction (at least one)
pip install pymupdf          # PyMuPDF (recommended, fastest)
pip install pdfplumber       # Alternative extraction engine

# For scanned PDFs
pip install pdf2image pytesseract  # OCR support
# Also install system binaries:
# - macOS: brew install tesseract poppler
# - Ubuntu: sudo apt install tesseract-ocr poppler-utils
# - Windows: Download from GitHub releases
```

## Confidence Scoring

### How It's Calculated
```
15 pts  → Name (full name = 15, partial = 7)
10 pts  → Email (valid = 10, invalid = 6)
20 pts  → Skills (5+ = 20, 3+ = 12, 1+ = 8)
20 pts  → Experience (1+ = 20)
15 pts  → Education (1+ = 15)
20 pts  → Projects (2+ = 20, 1 = 10)
────────────────
100 pts TOTAL
```

### Blocking Threshold
- **Default**: 70%
- **Configurable**: `MIN_RESUME_CONFIDENCE` environment variable

## Resume Blocking Rules

Pipeline **STOPS** if ANY of these:
```
✗ Confidence < 70%
✗ No name found
✗ 0 skills detected
✗ 0 experience entries
✗ 0 projects
```

If blocked:
- User sees validation card with ✓/✗ checklist
- Confidence score displayed
- Error message with actionable instructions
- "Upload different resume" button

## Parsed Resume Structure

### Location
```
resume_cache/resume_cache.json
```

### Example Structure
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1-555-123-4567",
  "linkedin": "https://linkedin.com/in/johndoe",
  "github": "https://github.com/johndoe",
  "skills": [
    "Python", "React", "AWS", "PostgreSQL", "Docker"
  ],
  "skills_categorized": {
    "languages": ["Python"],
    "frameworks": ["React"],
    "cloud": ["AWS", "Docker"],
    "databases": ["PostgreSQL"]
  },
  "experience": [
    {
      "company": "Tech Corp",
      "role": "Senior Engineer",
      "title": "Senior Software Engineer",
      "start_date": "2020",
      "end_date": null,
      "description": "Led backend team...",
      "technologies_used": ["Python", "AWS"]
    }
  ],
  "projects": [
    {
      "name": "AI Chat",
      "description": "LLM-based chatbot",
      "tech_stack": ["Python", "React", "LangChain"],
      "github": "github.com/johndoe/chat",
      "deployment": "https://chat.example.com"
    }
  ],
  "education": [
    {
      "institution": "MIT",
      "degree": "BS Computer Science",
      "field": "Computer Science",
      "cgpa": "3.8",
      "start_year": "2018",
      "end_year": "2022"
    }
  ],
  "target_roles": [
    "Backend Engineer",
    "Full Stack Developer",
    "Software Engineer"
  ],
  "confidence": 85,
  "extraction_stats": {
    "engine_used": "PyMuPDF",
    "chars_extracted": 12543,
    "pages": 2
  }
}
```

## Skills Categories

### Languages
Python, JavaScript, TypeScript, SQL, Java, C++, C#, Go, Rust, Ruby, PHP, Swift, Kotlin, Scala, R, MATLAB, Perl, Bash, Shell, and more

### Frameworks
React, Next.js, Vue.js, Angular, Django, Flask, FastAPI, Spring Boot, Express, Node.js, ASP.NET, Laravel, and more

### Databases
PostgreSQL, MySQL, MongoDB, Redis, Cassandra, Elasticsearch, DynamoDB, Firebase, Firestore, Neo4j, and more

### Cloud & DevOps
AWS, Azure, GCP, Docker, Kubernetes, Terraform, Ansible, Jenkins, GitHub Actions, Cloudflare

### AI/ML
Machine Learning, Deep Learning, NLP, Computer Vision, TensorFlow, PyTorch, OpenAI, HuggingFace, LangChain

### Tools
Git, GitHub, Jira, Confluence, Figma, Linux, REST, GraphQL, Tableau, Power BI, Spark, Kafka, Airflow

## API Events

### SSE Event: Blocked Resume

**Event Type**: `blocked`

```json
{
  "step": "blocked",
  "pct": 0,
  "msg": "Resume parsing confidence is 62% (minimum required: 70%)...",
  "blocked": true,
  "validation": {
    "name": true,
    "skills": false,
    "experience": true,
    "education": true,
    "projects": false,
    "confidence": 62
  }
}
```

## Debugging

### Enable Debug Logs
```python
import logging
logging.getLogger('resume_parser').setLevel(logging.DEBUG)
```

### Check Cache
```bash
# View cached resume
cat resume_cache/resume_cache.json | jq

# Check extraction stats
jq '.extraction_stats' resume_cache/resume_cache.json
```

### Log Levels
- `ERROR`: Extraction engine failed, missing dependencies
- `WARNING`: Section detection issue, low confidence
- `INFO`: Successful parsing, cache saved
- `DEBUG`: Engine details, per-section data

## Common Issues & Fixes

### "All PDF engines failed"
**Cause**: Missing extraction libraries  
**Fix**: `pip install pymupdf pdfplumber`

### "OCR: NOT INSTALLED"
**Cause**: Scanned PDF without OCR support  
**Fix**: `pip install pdf2image pytesseract` + install system binaries

### "Resume confidence is 45%"
**Cause**: Missing critical sections  
**Fix**: Upload DOCX or text-based PDF with name, skills, experience

### "Confidence is 100% but still blocked"
**Cause**: Missing projects or skills  
**Fix**: Check blocking conditions: requires skills AND projects

## Tuning

### Lower Blocking Threshold
```bash
MIN_RESUME_CONFIDENCE=60  # Default: 70
```

### Remove Project Requirement
Edit `orchestrator.py`:
```python
# Comment out:
# if not has_projects:
#     missing_critical.append("projects")
```

### Add More Skills
Edit `agents/resume_parser_agent.py`, add to `COMMON_SKILLS`:
```python
"Kubernetes", "Docker Compose", "Helm", "ArgoCD"
```

## Performance

- **Parsing time**: 2-8 seconds (varies by file size and engine)
- **Cache size**: ~50KB JSON
- **Memory**: +10-15MB (LLM model caching)
- **Extraction success rate**: >99% (with all engines installed)

## Support Files

- 📄 [PRODUCTION_UPGRADE.md](./PRODUCTION_UPGRADE.md) - Full technical details
- 📋 Implementation checklist and testing guide
- 🔍 Detailed confidence scoring breakdown
- 🛠️ Troubleshooting and customization options
