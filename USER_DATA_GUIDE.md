# User Data Guide

## Overview

The job application bot now uses a simple JSON file to store your personal information instead of parsing a resume PDF. This gives you complete control over what data is used in applications.

## Setup

### 1. Fill Out Your Information

Open `user_data.json` in the root directory and fill in your personal information. This file contains all the common fields that appear in job applications.

**Required fields** (you must fill these out):

- `contact.first_name`
- `contact.last_name`
- `contact.email`
- `contact.phone`
- `education.school`
- `education.degree`
- `education.major`
- At least one skill in `skills.programming_languages`, `skills.frameworks`, `skills.tools`, or `skills.technologies`

**Optional but recommended**:

- Work authorization information (important for US jobs)
- Past experiences
- Projects
- Complete education details (GPA, graduation date, etc.)

### 2. Fill Out Skills

The `skills` section has multiple categories:

```json
"skills": {
  "programming_languages": ["Python", "JavaScript", "Java"],
  "frameworks": ["React", "Django", "Spring Boot"],
  "tools": ["Git", "Docker", "AWS"],
  "technologies": ["REST APIs", "SQL", "NoSQL"],
  "soft_skills": ["Team collaboration", "Problem solving"],
  "languages_spoken": ["English", "Spanish"]
}
```

All of these will be combined and used for job matching.

### 3. Add Your Experiences

Add your work experience, internships, or relevant positions:

```json
"experience": [
  {
    "title": "Software Engineering Intern",
    "company": "Tech Company Inc.",
    "location": "San Francisco, CA",
    "start_date": "May 2024",
    "end_date": "August 2024",
    "currently_working": false,
    "description": "Built features for web application, collaborated with team..."
  }
]
```

### 4. Answer Common Questions

Fill out the `questions` section with your standard responses:

```json
"questions": {
  "cover_letter": "Your default cover letter text...",
  "why_interested": "I'm passionate about technology because...",
  "tell_us_about_yourself": "I'm a computer science student with..."
}
```

These will be used to pre-fill common application questions. The AI can also generate custom responses based on your profile.

## Usage

### Running the Full Pipeline

```bash
# With user data only (no resume PDF upload)
python run.py --user-data user_data.json

# With optional resume PDF for upload
python run.py --user-data user_data.json --resume-pdf resume.pdf
```

### Running Specific Stages

```bash
# Just scrape jobs
python run.py --scrape-only

# Scrape and match only (dry run)
python run.py --user-data user_data.json --dry-run

# Apply to matched jobs with manual review
python run.py --user-data user_data.json --manual-review
```

### Testing

Test with a single job:

```bash
python test_bandwidth_job.py
```

## How It Works

### 1. Job Matching

When you run the matching stage, the system:

1. Loads your `user_data.json` file
2. Creates a text summary of your profile (skills, experience, education)
3. Generates an AI embedding of your profile
4. Compares it against all scraped jobs
5. Marks jobs as "MATCHED" if they exceed the similarity threshold

### 2. Automatic Application

When you run the application stage, the system:

1. Loads your `user_data.json` file
2. Opens each matched job in a browser
3. Fills in standard fields (name, email, phone)
4. Uploads your resume PDF if you provided one
5. Uses AI to answer custom questions based on your profile
6. Submits the application (or shows you a review screen if `--manual-review` is enabled)

### 3. Smart Question Answering

The AI uses your profile to answer questions:

- Cover letters are generated based on your experience and the specific job
- Technical questions reference your actual skills
- Work authorization questions use your specified status
- Custom questions get contextual answers from your profile

## Validation

The system validates your data before running:

```
Warning: Missing required fields: contact.phone, education.gpa
```

You can ignore warnings for optional fields, but required fields must be filled in.

## Tips

### For Internships

Make sure to fill out the `internship_specific` section:

```json
"internship_specific": {
  "year_in_school": "Junior",
  "classification": "Undergraduate",
  "available_for_full_time_after": false,
  "preferred_start_date": "May 2026",
  "preferred_end_date": "August 2026"
}
```

### For Work Authorization

US companies often ask about work authorization:

```json
"work_authorization": {
  "us_citizen": true,
  "authorized_to_work_in_us": true,
  "require_visa_sponsorship": false,
  "require_sponsorship_now": false,
  "require_sponsorship_future": false
}
```

### For Better Matches

- Add specific technical skills that appear in job descriptions
- Include detailed project descriptions
- Fill out your education section completely
- Write thoughtful answers to the common questions

## Updating Your Information

You can edit `user_data.json` at any time. The changes will be used immediately the next time you run the bot.

No need to reparse or regenerate anything - just save the file and run again!

## Privacy

Your `user_data.json` file stays on your local machine. The only external services that see it are:

- OpenAI API (for embeddings and question answering)
- The job application websites (when submitting applications)

Consider adding `user_data.json` to your `.gitignore` if you're pushing this code to a public repository.

## Troubleshooting

### "User data file not found"

Make sure `user_data.json` is in the root directory of the project. You can also specify a different path:

```bash
python run.py --user-data /path/to/my/data.json
```

### "Missing required fields"

Check the error message and fill in the required fields in your JSON file. The system will tell you exactly what's missing.

### Applications not filling correctly

1. Check that your field names and values are correctly formatted
2. Review the screenshots saved in the `screenshots/` directory
3. Enable manual review to see what's happening: `--manual-review`

## Example: Filled User Data

See `user_data.json` for a complete template. Here's a minimal working example:

```json
{
  "contact": {
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "email": "john.doe@email.com",
    "phone": "+1-555-123-4567",
    "linkedin_url": "https://linkedin.com/in/johndoe"
  },
  "education": {
    "school": "State University",
    "degree": "Bachelor of Science",
    "major": "Computer Science",
    "gpa": "3.7",
    "expected_graduation": "May 2026"
  },
  "skills": {
    "programming_languages": ["Python", "JavaScript", "Java"],
    "frameworks": ["React", "Node.js", "Django"],
    "tools": ["Git", "Docker"]
  },
  "work_authorization": {
    "us_citizen": true,
    "require_visa_sponsorship": false
  }
}
```
