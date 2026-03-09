# Jobby — AI-Powered Job Search Agent

Automated job search and resume tailoring pipeline built with Python, Playwright, and Claude AI.

## What it does

- **Scrapes LinkedIn** across 40+ search queries and 15 US cities for Senior/Staff SRE, Platform Engineer, DevOps, and Solutions Architect roles
- **Filters intelligently** — blocks staffing agencies, wrong seniority levels, irrelevant domains, and international postings
- **Persists memory** across sessions — tracks job status (new → tailored → applied)
- **Tailors resumes** — fetches the job description, sends to Claude Opus, gets back a role-specific resume + cover letter with fit score
- **Outputs polished DOCX + PDF** — matching professional resume formatting with styled headers, skills table, inline bold keywords

## Stack

- Python 3.9 · Playwright (headless Chromium) · BeautifulSoup
- Anthropic Claude API (claude-opus-4-5)
- Node.js · docx library (DOCX generation)
- LibreOffice (PDF conversion)

## Usage
```bash
# Scrape latest jobs
python3 jobb_latest.py

# Tailor resume for a specific job
python3 tailor.py              # interactive picker
python3 tailor.py --index 3    # by job number
python3 tailor.py --link <url> # by LinkedIn URL

# Memory / job tracking
python3 memory.py stats
python3 memory.py last
python3 memory.py shortlist
```

## Roadmap

- [ ] Telegram approval flow — review jobs and trigger tailoring from phone
- [ ] Daily cron scheduler — runs every morning, sends new jobs to Telegram
- [ ] Auto-apply — Playwright fills LinkedIn Easy Apply forms automatically
- [ ] GCP Cloud Run deployment — fully automated pipeline in the cloud

