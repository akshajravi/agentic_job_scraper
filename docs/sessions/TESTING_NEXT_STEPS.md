# Next Steps: Resume Matching & Auto-Application Testing

## Current Status
✅ Job scraping complete - 1822 jobs in database
⏳ Resume matching - ready for testing
⏳ Auto-application - ready for testing

## Before You Start

### 1. Prepare Your Resume
Place your resume PDF at:
```bash
./resume.pdf
```

Or specify a custom path:
```bash
python run.py --resume /path/to/your/resume.pdf --dry-run
```

### 2. Set OpenAI API Key
Edit `.env` file:
```bash
OPENAI_API_KEY=sk-...your-key-here...
```

Get an API key from https://platform.openai.com/api-keys

## Test Plan

### Phase 1: Verify Scraping (Already Done ✅)
```bash
python run.py --scrape-only
```
Result: 1822 jobs scraped and stored

### Phase 2: Test Dry Run (Matching Only)
```bash
python run.py --resume resume.pdf --dry-run
```

What happens:
- Parses your resume
- Generates embedding from resume content
- Matches all 1822 jobs to your resume
- Displays top 10 matches
- **No applications sent**

Time: ~2-3 minutes

Expected output:
```
┏━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃Score ┃Company   ┃Title     ┃Location  ┃
┡━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│75.2% │Company A │SWE      │Remote     │
│71.8% │Company B │Backend  │NYC        │
└─────┴──────────┴──────────┴───────────┘
```

### Phase 3: Test Manual Review (1 Application)
```bash
python run.py --resume resume.pdf --manual-review --max-applications 1
```

What happens:
- Finds best matching Greenhouse job
- Opens browser with Greenhouse form
- Shows preview of answers to be submitted
- **Waits for your approval before submitting**
- Shows success/error after submission

Key controls:
- Review button: Open review UI
- Approve: Submit the application
- Skip: Don't apply to this job
- Edit: Modify answers before submitting

Time: ~1-2 minutes per application

### Phase 4: Test Full Auto-Application (5 Jobs)
```bash
python run.py --resume resume.pdf --max-applications 5
```

What happens:
- Finds top 5 matching Greenhouse jobs
- Automatically fills and submits applications
- **No browser window** (headless mode)
- Shows summary of results

Time: ~5-10 minutes

### Phase 5: Production Mode (Max Daily Limit)
```bash
python run.py --resume resume.pdf
```

What happens:
- Runs full 4-stage pipeline:
  1. Scrape jobs
  2. Match to resume
  3. Apply to max 10 Greenhouse positions
  4. Send email summary
- No manual intervention

## Debugging Tips

### See What's Matching
```python
from agent.storage.db import get_db
from agent.storage.models import Job, JobStatus

with get_db() as db:
    matches = db.query(Job).filter_by(status=JobStatus.MATCHED).order_by(
        Job.match_score.desc()
    ).limit(5).all()

    for job in matches:
        print(f"{job.match_score:.1%} - {job.title} at {job.company}")
```

### Check Application Errors
```python
from agent.storage.db import get_db
from agent.storage.models import Application, ApplicationStatus

with get_db() as db:
    errors = db.query(Application).filter_by(
        status=ApplicationStatus.FAILED
    ).all()

    for app in errors:
        print(f"Job {app.job_id}: {app.error_message}")
```

### Verify Job Sources
```python
from agent.storage.db import get_db
from agent.storage.models import Job

with get_db() as db:
    from sqlalchemy import func
    by_source = db.query(
        Job.source,
        func.count(Job.id).label('count')
    ).group_by(Job.source).all()

    for source, count in by_source:
        print(f"{source}: {count}")
```

## Expected Issues & Solutions

### Issue: "OpenAI API Error: Invalid API key"
**Solution:**
1. Check `.env` file has `OPENAI_API_KEY=sk-...`
2. Verify key is correct at https://platform.openai.com/api-keys
3. Check key isn't expired or revoked

### Issue: "No matched Greenhouse jobs to apply to"
**Solution:**
1. Some jobs may use other ATS systems (Lever, Workday, Ashby)
2. Only Greenhouse is currently supported for auto-apply
3. Try `--dry-run` to see which jobs matched

### Issue: "Timeout waiting for job form to load"
**Solution:**
1. Greenhouse site might be slow - network issue
2. Increase timeout in `.env`: `BROWSER_TIMEOUT=60`
3. Try with `--manual-review` to see actual page

### Issue: "Resume file not found"
**Solution:**
1. Ensure `./resume.pdf` exists in project root
2. Or specify full path: `--resume /Users/name/Documents/resume.pdf`

## Configuration Tuning

### Adjust Match Sensitivity
In `.env`:
```bash
MATCH_THRESHOLD=0.7    # Default: 75% similarity
MATCH_THRESHOLD=0.6    # Lower = more matches
MATCH_THRESHOLD=0.8    # Higher = stricter matching
```

### Set Application Limits
```bash
MAX_APPLICATIONS_PER_DAY=10    # Default
MAX_APPLICATIONS_PER_DAY=5     # Conservative
MAX_APPLICATIONS_PER_DAY=20    # Aggressive
```

### Enable Email Notifications
```bash
EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
NOTIFICATION_EMAIL=where-to-send-summary@example.com
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

## Success Metrics

### Dry Run (Phase 2)
✅ Resume parses without errors
✅ At least 1 job matches
✅ Top 10 matches display correctly

### Manual Review (Phase 3)
✅ Browser opens to Greenhouse form
✅ Form shows correct job information
✅ Review UI displays with answers
✅ Can approve/reject before submitting

### Auto-Application (Phase 4)
✅ Applications submit successfully
✅ Success messages appear
✅ Database records applications
✅ Error messages are clear if issues occur

## Next Actions

1. **Prepare resume.pdf** in project root
2. **Set OPENAI_API_KEY** in .env
3. **Run Phase 2**: `python run.py --resume resume.pdf --dry-run`
4. **Review matches** and note which companies interest you
5. **Test Phase 3** with 1 application to verify workflow
6. **Expand to Phase 4** for multiple auto-applications

Good luck! 🚀
