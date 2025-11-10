# Job Scraping Complete ✅

## Summary
Successfully scraped and stored **1822 job listings** from GitHub repositories across multiple job boards.

## Data Breakdown

### Jobs by Source
| Source | Count | Format |
|--------|-------|--------|
| SimplifyJobs/Summer2025-Internships | 1051 | HTML tables in markdown |
| cvrve/New-Grad-2025 | 531 | Markdown pipe tables |
| ReaVNaiL/New-Grad-2024 | 240 | Markdown pipe tables |
| **Total** | **1822** | - |

### ATS Distribution
The 1822 jobs are distributed across various Applicant Tracking Systems:
- Greenhouse.io
- Lever.co
- Workday
- Ashby
- Unknown/Direct applications

## Technical Improvements

### HTML Table Parser Enhancement
The scraper was updated to handle both:
1. **Pure Markdown Tables** (pipe-delimited)
2. **HTML Tables Embedded in Markdown** (SimplifyJobs format)

The parser now:
- Attempts HTML parsing first (returns jobs if found)
- Falls back to markdown parsing for traditional formats
- Extracts URLs from:
  - Markdown link syntax: `[text](url)`
  - Plain URLs in text
  - HTML anchor tags (even in cells with no text content)

### Key Fix
SimplifyJobs tables have a unique structure where:
- Company name is in Cell 0 (with marketing link)
- Job title is in Cell 1
- Location is in Cell 2
- **Application URL is in Cell 3 as a hidden link** (no visible text)

The updated parser checks HTML cell objects for anchor tags to extract these hidden links.

## Next Steps

### 1. Resume Matching (--dry-run)
```bash
python run.py --resume resume.pdf --dry-run
```

Requires:
- Valid resume PDF at `./resume.pdf`
- OpenAI API key in `.env` with `OPENAI_API_KEY=sk-...`

This will:
- Parse resume and generate embeddings
- Match all 1822 jobs using cosine similarity
- Display top 10 matches

### 2. Manual Review & Application
```bash
python run.py --resume resume.pdf --manual-review --max-applications 5
```

This will:
- Show a browser window for each Greenhouse application
- Display a review UI before submitting
- Allow you to approve, reject, or edit answers
- Submit applications automatically on approval

### 3. Full Pipeline
```bash
python run.py --resume resume.pdf
```

This runs all stages:
1. Scrape jobs
2. Match to resume
3. Apply to Greenhouse positions
4. Send email summary

## Configuration

All settings are in `.env` - see `.env.example` for full list:

**Required:**
- `OPENAI_API_KEY` - For resume parsing and matching

**Optional:**
- `MATCH_THRESHOLD` - Minimum similarity score (default: 0.7)
- `AUTO_APPLY` - Enable automatic applications (default: False)
- `MAX_APPLICATIONS_PER_DAY` - Max apps per run (default: 10)
- Email notifications (SMTP settings)

## Database Stats
- Total Records: 1822
- Status: All NEW (not yet matched)
- Database File: `./jobs.db` (SQLite)

## Troubleshooting

### No jobs showing from SimplifyJobs?
Check if HTML parsing is enabled (it should be by default).

### Getting 0 matches?
- Verify `OPENAI_API_KEY` is set correctly
- Check `MATCH_THRESHOLD` isn't too high
- Ensure resume.pdf exists and has content

### Applications not submitting?
- Only Greenhouse positions are currently supported
- Check if positions are Greenhouse (check URL in job listing)
- Enable `--manual-review` to see what's happening
