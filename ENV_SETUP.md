# Environment Variables Setup Guide

Copy `.env.example` to `.env` and configure these settings:

```bash
cp .env.example .env
```

Then edit `.env` with your values. Here's what each setting means:

---

## Required Settings

### OPENAI_API_KEY (REQUIRED)
**What it is:** Your OpenAI API key for GPT-4 and embeddings

**How to get it:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (you can only see it once!)
4. Paste into `.env`

**Example:**
```env
OPENAI_API_KEY=sk-proj-abc123xyz789...
```

**Cost:** ~$0.01-0.15 per run depending on number of jobs and applications

**Check balance:** https://platform.openai.com/usage/overview

---

## Optional Settings (Email Notifications)

### EMAIL_HOST
**What it is:** SMTP mail server address

**Default:** `smtp.gmail.com` (for Gmail)

**For other providers:**
- Outlook/Hotmail: `smtp-mail.outlook.com`
- Yahoo: `smtp.mail.yahoo.com`
- Custom domain: Ask your email provider

```env
EMAIL_HOST=smtp.gmail.com
```

---

### EMAIL_PORT
**What it is:** SMTP port number

**Default:** `587` (recommended - TLS)

**Common ports:**
- `587` - TLS (Start with this)
- `465` - SSL
- `25` - Unencrypted (not recommended)

```env
EMAIL_PORT=587
```

---

### EMAIL_USER
**What it is:** Your email address (username for SMTP)

**For Gmail:** Use your Gmail email address
**For others:** Use your full email address

**Example:**
```env
EMAIL_USER=your-email@gmail.com
```

---

### EMAIL_PASSWORD
**What it is:** Password for SMTP authentication

**⚠️ IMPORTANT - For Gmail Users:**
- Do NOT use your regular Gmail password
- Use an "App Password" instead
- Follow this guide: https://support.google.com/accounts/answer/185833

**Steps for Gmail:**
1. Go to https://myaccount.google.com/
2. Left menu → "Security"
3. Scroll down → "App passwords" (requires 2FA enabled)
4. Select "Mail" and "Windows Computer" (or your device)
5. Google generates a 16-character password
6. Copy and paste into `.env`

**For other providers:**
- Use your regular password or check their "app password" system

**Example:**
```env
EMAIL_PASSWORD=abcd efgh ijkl mnop
```

---

### EMAIL_TO
**What it is:** Where to send notification emails

**Can be same as EMAIL_USER or different**

**Example:**
```env
EMAIL_TO=your-email@gmail.com
```

**Note:** If email config is not complete, notifications will be skipped (no error)

---

## Application Settings

### AUTO_APPLY
**What it is:** Whether to automatically submit applications

**Options:**
- `false` (default) - Never auto-apply, always require manual review or `--manual-review` flag
- `true` - Auto-apply without asking (use with caution!)

**Recommendation:** Keep as `false` unless you're very confident

```env
AUTO_APPLY=false
```

---

### MAX_APPLICATIONS_PER_DAY
**What it is:** Maximum applications to send per run

**Default:** `10`

**Use cases:**
- Testing: `1`
- Conservative: `3-5`
- Normal: `10`
- Aggressive: `20+`

**Note:** This is a soft limit; you can override with CLI: `--max-applications 5`

```env
MAX_APPLICATIONS_PER_DAY=10
```

---

### MATCH_THRESHOLD
**What it is:** Minimum job match score to consider (0.0 to 1.0)

**Default:** `0.7`

**Meaning:**
- `0.7` = 70% similarity with your resume (recommended)
- `0.8` = 80% similarity (very strict, fewer matches)
- `0.6` = 60% similarity (more matches but lower quality)

**Recommendation:** Start with `0.7`, adjust based on results

```env
MATCH_THRESHOLD=0.7
```

**Can override:** `python run.py --match-threshold 0.65`

---

## Browser Settings

### HEADLESS
**What it is:** Whether to hide the browser window

**Options:**
- `false` (default) - Show browser window (good for debugging)
- `true` - Hide browser window (for automated runs)

**Recommendation:**
- Use `false` for testing and manual review
- Can use `true` for scheduled jobs

```env
HEADLESS=false
```

**Note:** Manual review mode automatically shows the browser regardless

---

### BROWSER_TIMEOUT
**What it is:** How long to wait for page elements (milliseconds)

**Default:** `30000` (30 seconds)

**Adjust if:**
- `TimeoutError` on slow internet: Increase to `45000`
- Want faster failures: Decrease to `15000`

```env
BROWSER_TIMEOUT=30000
```

---

## Advanced Settings

### DATABASE_URL
**What it is:** SQLite database connection string

**Default:** `sqlite:///./jobs.db` (creates in project directory)

**Keep as default for local use:**
```env
DATABASE_URL=sqlite:///./jobs.db
```

---

### LOG_LEVEL
**What it is:** Verbosity of logging output

**Options:**
- `DEBUG` - Very verbose (development)
- `INFO` - Normal (default, recommended)
- `WARNING` - Only warnings and errors
- `ERROR` - Only errors

**Recommendation:** Start with `INFO`

```env
LOG_LEVEL=INFO
```

---

### ANTHROPIC_API_KEY (Optional)
**What it is:** Anthropic API key for future use

**Can leave empty for now:**
```env
ANTHROPIC_API_KEY=
```

---

## Example Complete .env File

```env
# REQUIRED
OPENAI_API_KEY=sk-proj-abc123...

# Email (optional, can leave blank to skip)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop
EMAIL_TO=your-email@gmail.com

# Application Settings
AUTO_APPLY=false
MAX_APPLICATIONS_PER_DAY=10
MATCH_THRESHOLD=0.7

# Browser Settings
HEADLESS=false
BROWSER_TIMEOUT=30000

# Database
DATABASE_URL=sqlite:///./jobs.db

# Logging
LOG_LEVEL=INFO

# Optional
ANTHROPIC_API_KEY=
```

---

## Minimal .env (Just for Testing)

If you just want to test without email:

```env
OPENAI_API_KEY=sk-proj-your-key-here
AUTO_APPLY=false
HEADLESS=false
LOG_LEVEL=INFO
```

---

## Testing Your Configuration

### 1. Test OpenAI API Key
```bash
python -c "
from agent.config import settings
print(f'OpenAI API Key: {settings.openai_api_key[:20]}...')
print(f'Match Threshold: {settings.match_threshold}')
print(f'Max Applications: {settings.max_applications_per_day}')
"
```

### 2. Test Email Configuration (optional)
```bash
python -c "
from agent.notify.email import EmailNotifier
notifier = EmailNotifier()
success = notifier.send_summary(
    {'scraped': 0, 'matched': 0, 'applied': 0, 'successful': 0}
)
print(f'Email test: {'Success' if success else 'Not configured or failed'}')
"
```

### 3. Test Everything
```bash
python run.py --scrape-only
```

---

## Troubleshooting

### OpenAI Error: "Invalid API key"
- Check key is correct: https://platform.openai.com/api-keys
- Key should start with `sk-proj-` or `sk-`
- No spaces before/after the key

### OpenAI Error: "Insufficient quota"
- Out of credits or trial expired
- Add payment method: https://platform.openai.com/account/billing/overview

### Email not sending
- Try with just Gmail first to test
- For Gmail: Enable 2FA and use App Password
- For others: Check SMTP settings with your provider
- Test manually:
  ```bash
  python agent/notify/email.py
  ```

### Browser not showing
- Check `HEADLESS=false` in .env
- Try: `python run.py --resume resume.pdf --dry-run`

### Database errors
- Delete `jobs.db` and try again
- Or specify different path in `DATABASE_URL`

---

## Security Notes

- ⚠️ Never commit `.env` file to git (already in `.gitignore`)
- Keep API keys private - don't share `.env`
- Use App Passwords for Gmail instead of main password
- Rotate API keys regularly: https://platform.openai.com/api-keys

---

## Environment Variables Loaded From

The app loads settings from (in order):
1. `.env` file (in project root)
2. System environment variables
3. Default values in `agent/config.py`

You can also set directly in shell:
```bash
export OPENAI_API_KEY=sk-your-key
python run.py --resume resume.pdf --dry-run
```

---

## Quick Setup Checklist

- [ ] Got OpenAI API key from https://platform.openai.com/api-keys
- [ ] Created `.env` file from `.env.example`
- [ ] Added `OPENAI_API_KEY` to `.env`
- [ ] Tested config: `python run.py --scrape-only`
- [ ] (Optional) Configured email settings
- [ ] (Optional) Tested email: Created test run with `--dry-run`

Ready to test! 🚀
