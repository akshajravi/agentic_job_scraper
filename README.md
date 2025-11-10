# Agentic Job Scraper & Auto-Applier

Automatically scrape job listings, match them to your resume, and apply to positions.

## What it does

1. **Scrapes jobs** from GitHub repositories (1800+ listings)
2. **Parses your resume** using OpenAI to extract skills and experience
3. **Matches jobs** to your resume using AI embeddings
4. **Applies automatically** to Greenhouse positions with AI-generated answers
5. **Sends email** with a summary of applications

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/akshajravi/agentic_job_scraper.git
cd agentic_job_scraper

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

### 2. Configure

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-key-here
```

Optional - for email notifications:
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_TO=your-email@gmail.com
```

**For Gmail**: Use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### 3. Run

```bash
# See matches without applying
python run.py --resume resume.pdf --dry-run

# Apply with manual review for each job
python run.py --resume resume.pdf --manual-review --max-applications 5

# Apply automatically (up to 10 jobs)
python run.py --resume resume.pdf
```

## Commands

```
--resume PATH              Path to your resume PDF
--dry-run                  Scrape and match only, don't apply
--manual-review            Review each application before submitting
--max-applications N       Max number of jobs to apply to (default: 10)
--scrape-only              Only scrape jobs, don't match or apply
--match-threshold FLOAT    Min match score 0.0-1.0 (default: 0.7)
```

## Project Structure

```
agent/
  ingest/              # Scraping
    github_repos.py
    normalize.py
  match/               # Resume parsing & matching
    resume_parser.py
    embed_matcher.py
  apply/               # Job applications
    greenhouse.py
    review_ui.py
  notify/              # Email notifications
    email.py
  storage/             # Database
    db.py
    models.py
```

## How it works

### Scraping
Fetches job listings from GitHub repositories containing job board compilations.

**Current sources**:
- SimplifyJobs/Summer2025-Internships: 1051 jobs
- cvrve/New-Grad-2025: 531 jobs
- ReaVNaiL/New-Grad-2024: 240 jobs

Supports both markdown and HTML table formats.

### Matching
1. Parses your resume PDF and extracts text
2. Generates an embedding of your resume using OpenAI
3. For each job, calculates similarity score
4. Returns matches above 70% similarity (configurable)

### Applying
Currently supports **Greenhouse** only. The system:
1. Opens the application form in a browser
2. Detects custom questions
3. Uses GPT-4 to generate answers based on your resume
4. Fills and submits the form

With `--manual-review`, you can edit answers before submitting.

### Database
Jobs and applications are stored in `jobs.db` (SQLite).

Track status: NEW → MATCHED → APPLIED

## Configuration

Key settings in `.env`:

| Setting | Purpose | Default |
|---------|---------|---------|
| `OPENAI_API_KEY` | Required for parsing & matching | - |
| `MATCH_THRESHOLD` | Min match score (0.0-1.0) | 0.7 |
| `MAX_APPLICATIONS_PER_DAY` | Max apps per run | 10 |
| `HEADLESS` | Hide browser window | false |
| `BROWSER_TIMEOUT` | Timeout in ms | 30000 |

## Troubleshooting

**Resume parsing fails**
- Make sure the PDF is text-based (not scanned)
- Check that OPENAI_API_KEY is set correctly

**No jobs matched**
- Lower the threshold: `--match-threshold 0.6`
- Check resume was parsed: `python run.py --scrape-only`

**Browser automation fails**
- Run: `playwright install chromium`
- Try with `HEADLESS=false` to see what's happening

**Email not sending**
- Verify SMTP settings in `.env`
- For Gmail, use an App Password (not regular password)

## Safety

- **Manual review mode** lets you review before applying
- **Rate limiting** (max 10 apps/day by default)
- **Dry-run mode** tests without submitting
- **Auto-apply is disabled by default** - must be explicitly enabled

## Cost

Using OpenAI APIs:
- Resume parsing: ~$0.01
- Job matching: ~$0.02 per 100 jobs
- Question answering: ~$0.01 per question

**Estimated**: ~$2-3 for 100 applications



**Use at your own risk.** The authors are not responsible for any consequences.

## Credits

- Jobs sourced from: [SimplifyJobs](https://github.com/SimplifyJobs), [ReaVNaiL](https://github.com/ReaVNaiL), [cvrve](https://github.com/cvrve)
- Built with: OpenAI, Playwright, SQLAlchemy, Rich
