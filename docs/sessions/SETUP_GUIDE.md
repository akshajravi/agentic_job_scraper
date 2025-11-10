# Quick Setup Guide

## Implementation Complete!

All core components have been implemented for the Greenhouse auto-applier pipeline. Here's what was built:

### New Files Created

#### Core Modules
1. **agent/match/resume_parser.py** - PDF parsing with GPT-4 extraction
2. **agent/match/embed_matcher.py** - OpenAI embeddings for job matching
3. **agent/apply/greenhouse.py** - Playwright automation for Greenhouse ATS
4. **agent/apply/review_ui.py** - Beautiful HTML review interface
5. **agent/notify/email.py** - Email notification service
6. **run.py** - Main orchestrator with Rich CLI

#### Configuration Files
- **.env.example** - Environment variable template
- **README.md** - Comprehensive documentation
- **.gitignore** - Git ignore rules
- **requirements.txt** - Updated with pdfplumber and rich

## Next Steps to Test

### 1. Install Dependencies

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Install new dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 2. Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit .env and add your OpenAI API key
# At minimum, you need:
OPENAI_API_KEY=sk-your-key-here
```

### 3. Prepare Your Resume

Place your resume PDF in the project directory, e.g., `resume.pdf`

### 4. Test the Pipeline

**Option A: Dry Run (Recommended First)**
```bash
python run.py --resume resume.pdf --dry-run
```
This will:
- Scrape jobs from GitHub repos
- Parse your resume
- Match jobs using AI embeddings
- Show you top matches
- **NOT apply to any jobs**

**Option B: Apply with Manual Review**
```bash
python run.py --resume resume.pdf --manual-review --max-applications 1
```
This will:
- Do everything from dry run
- Open a browser window showing the application preview
- Let you review and edit AI-generated answers
- Wait for you to click "Submit" or "Skip"

**Option C: Scrape Only (Test First Stage)**
```bash
python run.py --scrape-only
```

### 5. Check the Output

After running, you should see:
- Beautiful colored terminal output with progress bars
- Statistics about jobs scraped and matched
- A table showing top job matches
- Database file created: `jobs.db`
- Screenshots in `screenshots/` directory (if errors occur)

## Troubleshooting First Run

### If resume parsing fails:
```bash
# Check that your PDF is text-based (not scanned)
# Try opening it in Preview/Adobe to verify text is selectable
```

### If no jobs are scraped:
```bash
# Check internet connection
# Verify GitHub repos are accessible
```

### If OpenAI API errors:
```bash
# Verify API key in .env file
# Check API key has credits: https://platform.openai.com/usage
```

### If Playwright errors:
```bash
# Reinstall browser
playwright install --force chromium
```

## Understanding the Output

### Terminal Output Example:
```
┌────────────────────────────────────────┐
│ Agentic Job Scraper & Auto-Applier    │
│ Scrape: True | Match: True | Apply: True │
└────────────────────────────────────────┘

┌─ Stage 1: Scraping Jobs from GitHub ─┐
  ✓ SimplifyJobs/Summer2025-Internships: 245 jobs (23 new)
  ✓ ReaVNaiL/New-Grad-2025: 189 jobs (15 new)

Results: 38 new jobs, 396 duplicates skipped

┌─ Stage 2: Matching Jobs to Resume ─┐
  ✓ Resume parsed
  ✓ Matched 12 jobs

Top Matched Jobs
┌────────┬──────────┬────────────────┬──────────┐
│ Score  │ Company  │ Title          │ Location │
├────────┼──────────┼────────────────┼──────────┤
│ 89.5%  │ Google   │ SWE Intern     │ Remote   │
│ 85.2%  │ Meta     │ Backend Eng    │ NYC      │
└────────┴──────────┴────────────────┴──────────┘
```

## Database Inspection

To view the database:
```bash
# Install sqlite3 (usually pre-installed on Mac/Linux)
sqlite3 jobs.db

# View tables
.tables

# View jobs
SELECT company, title, match_score FROM jobs WHERE status = 'MATCHED' ORDER BY match_score DESC LIMIT 10;

# Exit
.quit
```

## Manual Review UI

When you run with `--manual-review`, you'll see:
- A beautiful web page opens in your browser
- Job details with match score and reasoning
- All form fields with AI-generated answers
- Editable text boxes for each answer
- Two buttons: "Submit Application" and "Skip This Job"

You can edit any answer before submitting!

## What to Expect

### Costs (OpenAI API):
- Resume parsing: ~$0.01
- Matching 100 jobs: ~$0.02
- 10 applications with custom questions: ~$0.10
- **Total for testing**: < $0.25

### Time:
- Scraping: 30-60 seconds
- Resume parsing: 5-10 seconds
- Matching: 20-30 seconds per 100 jobs
- Each application: 30-60 seconds

### Success Rate:
- First run might have some issues (this is normal!)
- Greenhouse forms vary by company
- Some custom questions might not be detected
- Screenshots will help debug failures

## Recommended Testing Order

1. **Scrape only** - Verify GitHub scraping works
2. **Dry run** - Verify resume parsing and matching works
3. **Manual review with 1 job** - Test the full pipeline safely
4. **Manual review with 3-5 jobs** - Build confidence
5. **Consider automation** - Only after you're comfortable

## Need Help?

Check these files:
- **README.md** - Full documentation
- **agent/config.py** - See all available settings
- **.env.example** - All environment variables
- **run.py --help** - Command-line options

## Safety Reminders

- Start with `--dry-run` to test without applying
- Use `--manual-review` to verify each application
- Set `--max-applications 1` for first real test
- Check screenshots in `screenshots/` after errors
- Rate limit is 10 apps/day by default (configurable)

Good luck! 🚀
