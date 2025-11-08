# "How Did You Hear About Us" Smart Answer Feature

## Overview

Added intelligent handling for "How did you hear about this position?" questions with **automatic fallback logic** for dropdown menus.

## How It Works

### 📝 Text/Textarea Fields

Simple - just fills in "Corporate Website"

```
Question: "How did you hear about this position?"
Field Type: Text box
Answer: "Corporate Website" ✓
```

### 🔽 Dropdown/Select Fields (Smart Fallback)

Tries multiple options in order:

1. **First try**: "Corporate Website" (exact match)
2. **If not found**: "Other" (fallback)
3. **If "Other" not found**: Try case-insensitive match for any option containing "other"

```
Question: "How did you hear about this position?"
Field Type: Dropdown
Options: ["Company Website", "LinkedIn", "Referral", "Other"]

Attempt 1: Try "Corporate Website" → ❌ Not found
Attempt 2: Try "Other" → ✓ Selected!
```

### 📋 Follow-up "Please Specify" Fields

After selecting "Other", many forms show a text box asking "Please specify":

```
Previously selected: "Other" in dropdown
New question appears: "Please specify:"
Answer: "Corporate Website" ✓
```

## Patterns That Trigger This Answer

All of these questions will automatically get "Corporate Website" as the answer:

| Pattern                   | Example Questions                           |
| ------------------------- | ------------------------------------------- |
| `"how did you hear"`      | "How did you hear about this position?"     |
| `"how did you find"`      | "How did you find out about this role?"     |
| `"where did you hear"`    | "Where did you hear about us?"              |
| `"where did you find"`    | "Where did you find this job posting?"      |
| `"how did you learn"`     | "How did you learn about this opportunity?" |
| `"hear about this"`       | "How did you hear about this opening?"      |
| `"find this position"`    | "How did you find this position?"           |
| `"find this job"`         | "Where did you find this job?"              |
| `"source of application"` | "What is your source of application?"       |
| `"source of referral"`    | "Source of referral?"                       |
| `"please specify"`        | "Please specify:" (follow-up field)         |
| `"specify other"`         | "If other, please specify:"                 |
| `"if other"`              | "If other, specify:"                        |

## Example Flow in Real Application

### Scenario 1: Dropdown with "Corporate Website" option

```
1. Question detected: "How did you hear about us?"
2. Check predetermined answers → Found match!
3. Answer: "Corporate Website"
4. Try to select "Corporate Website" from dropdown → ✓ Success
5. Log: "Selected option: Corporate Website"
```

### Scenario 2: Dropdown WITHOUT "Corporate Website" option

```
1. Question detected: "How did you hear about this position?"
2. Check predetermined answers → Found match!
3. Answer: "Corporate Website"
4. Try to select "Corporate Website" from dropdown → ❌ Not in options
5. Fallback: Try "Other" → ✓ Success
6. Log: "Option 'Corporate Website' not found, trying 'Other'..."
7. Log: "Selected 'Other' as fallback"
8. System detects follow-up question: "Please specify:"
9. Check predetermined answers → Matches "please specify"!
10. Fill text field with "Corporate Website" → ✓ Done
```

### Scenario 3: Simple text field

```
1. Question detected: "Where did you find this job posting?"
2. Check predetermined answers → Found match!
3. Answer: "Corporate Website"
4. Fill text field with "Corporate Website" → ✓ Done
```

## What You'll See in Logs

### Successful exact match (dropdown):

```
INFO: Processing question: How did you hear about this position?
INFO: ✓ Matched predetermined answer for 'how did you hear': Corporate Website
INFO: Using predetermined answer: Corporate Website (saved API call)
INFO: Selected option: Corporate Website
INFO: Filled custom field: How did you hear about this position?
```

### Fallback to "Other" (dropdown):

```
INFO: Processing question: How did you hear about us?
INFO: ✓ Matched predetermined answer for 'how did you hear': Corporate Website
INFO: Using predetermined answer: Corporate Website (saved API call)
INFO: Option 'Corporate Website' not found, trying 'Other'...
INFO: Selected 'Other' as fallback
INFO: Filled custom field: How did you hear about us?
```

### Text field:

```
INFO: Processing question: Please specify your source:
INFO: ✓ Matched predetermined answer for 'please specify': Corporate Website
INFO: Using predetermined answer: Corporate Website (saved API call)
INFO: Filled custom field: Please specify your source:
```

## Customization

### Change the answer to something else:

Edit `agent/config.py`:

```python
predetermined_answers: dict[str, str] = {
    # Change from "Corporate Website" to your preference:
    "how did you hear": "LinkedIn",
    "how did you find": "LinkedIn",
    # ... update all the patterns you want to change
}
```

### Add more patterns:

```python
predetermined_answers: dict[str, str] = {
    # ... existing patterns ...

    # Add your own:
    "referral source": "Corporate Website",
    "job source": "Corporate Website",
}
```

## Why This Saves Money

**Before this feature:**

- "How did you hear?" → OpenAI API call ($0.003)
- "Please specify:" → OpenAI API call ($0.003)
- Total: $0.006 per application

**After this feature:**

- "How did you hear?" → Predetermined answer (FREE)
- "Please specify:" → Predetermined answer (FREE)
- Total: $0.00 per application

**Savings: $0.006 per application**

With these questions appearing on ~70% of applications:

- 10 applications/day × 30 days × 70% = 210 applications/month
- Savings: 210 × $0.006 = **$1.26/month**

Combined with all other predetermined answers:

- **Total monthly savings: $6-18**

## Edge Cases Handled

✅ **Case-insensitive matching**: "other", "Other", "OTHER" all work  
✅ **Partial matches**: "Other (please specify)" will match "other"  
✅ **No "Other" option**: Falls back gracefully and logs error  
✅ **Multiple "specify" fields**: Each gets "Corporate Website"  
✅ **Different field types**: Works for text, textarea, and select fields

## Testing

Test the feature:

```bash
python test_predetermined_answers.py
```

You'll see:

```
✓ Question: How did you hear about this position?
  Pattern matched: 'how did you hear'
  Answer: Corporate Website
  API call saved: $0.002-0.005

✓ Question: Please specify your source:
  Pattern matched: 'please specify'
  Answer: Corporate Website
  API call saved: $0.002-0.005
```

## Summary

✅ **Smart answer**: "Corporate Website" for all "How did you hear?" variations  
✅ **Automatic fallback**: Tries "Other" if exact match not in dropdown  
✅ **Handles follow-ups**: "Please specify" also gets "Corporate Website"  
✅ **Saves money**: No OpenAI API calls for these common questions  
✅ **Flexible**: Easy to customize in config.py  
✅ **Robust**: Handles edge cases and different field types

This feature makes your bot smarter and more cost-efficient! 🎉
