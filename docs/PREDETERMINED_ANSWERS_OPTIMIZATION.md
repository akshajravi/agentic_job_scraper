# Predetermined Answers Optimization

## Problem

Previously, the system was making an OpenAI API call for **every single question** in job applications, even simple yes/no questions like:

- "Do you have any conflicts of interest?" → Should be "No"
- "Have you worked here before?" → Should be "No"
- "Are you authorized to work?" → Should be "Yes"

This was **inefficient and expensive**, costing $0.002-0.005 per API call.

## Solution

Implemented a two-tier approach:

1. **Check predetermined answers first** (no API call needed)
2. **Use OpenAI only for creative questions** (personalized responses)

## What Changed

### 1. Added Predetermined Answers to Config (`agent/config.py`)

Added a dictionary of common question patterns and their answers:

```python
predetermined_answers: dict[str, str] = {
    # Conflict of interest questions
    "conflicts": "No",
    "conflict of interest": "No",

    # Previous employment questions
    "worked here before": "No",
    "previously employed": "No",

    # Legal/compliance questions
    "authorized to work": "Yes",
    "require sponsorship": "No",

    # And more...
}
```

### 2. Updated Greenhouse Applier (`agent/apply/greenhouse.py`)

#### Added `_check_predetermined_answer()` method:

- Checks if a question matches any predetermined pattern
- Returns the answer immediately if found
- Returns `None` if no match (triggers OpenAI call)

#### Updated `_answer_custom_question()` method:

```python
def _answer_custom_question(self, question: str, ...):
    # STEP 1: Check predetermined answers first (no API call!)
    predetermined = self._check_predetermined_answer(question)
    if predetermined:
        return predetermined  # Saved an API call!

    # STEP 2: Use OpenAI for creative questions
    return self._call_openai_api(...)  # Only when needed
```

## How It Works

### Example: Application with Mixed Questions

**Simple Questions (use predetermined answers):**

- ✓ "Do you have any conflicts?" → "No" (saved $0.003)
- ✓ "Have you worked here?" → "No" (saved $0.003)
- ✓ "Are you authorized to work?" → "Yes" (saved $0.003)
- ✓ "Do you need sponsorship?" → "No" (saved $0.003)

**Creative Questions (still use OpenAI):**

- 🤖 "Why do you want to work here?" → (calls OpenAI for personalized answer)
- 🤖 "Tell us about a challenging project" → (calls OpenAI for personalized answer)

### Cost Savings

- **Before**: 6 questions × $0.003 = $0.018 per application
- **After**: 2 questions × $0.003 = $0.006 per application
- **Savings**: 67% reduction in API costs

With 10 applications/day:

- **Monthly savings**: $3-15
- **Annual savings**: $36-180

## How to Add More Predetermined Answers

Edit `agent/config.py` and add patterns to the `predetermined_answers` dictionary:

```python
predetermined_answers: dict[str, str] = {
    # Your existing patterns...

    # Add new patterns here:
    "your pattern": "Your Answer",
    "another pattern": "Another Answer",
}
```

### Tips for Adding Patterns:

1. **Use lowercase keywords** from the question
2. **Match the key phrase**, not the entire question
3. **Be specific enough** to avoid false matches

**Good examples:**

```python
"conflicts": "No"  # Matches "Do you have any conflicts?"
"worked here": "No"  # Matches "Have you worked here before?"
```

**Bad examples:**

```python
"you": "No"  # Too generic - would match too many questions
"do you have": "No"  # Too vague - could match many different questions
```

## Logging

When the system processes questions, you'll see:

```
INFO: Processing question: Do you have any conflicts of interest?
INFO: ✓ Matched predetermined answer for 'conflicts': No
INFO: Using predetermined answer: No (saved API call)
```

vs.

```
INFO: Processing question: Why do you want to work here?
INFO: No predetermined answer found - using OpenAI API
INFO: Generated answer via OpenAI (length: 234 chars)
```

## Testing

Run the test script to see the optimization in action:

```bash
python test_predetermined_answers.py
```

This shows:

- Which patterns are configured
- Which questions match (save API calls)
- Which questions still need OpenAI
- Estimated cost savings

## Customization

You can customize your predetermined answers based on your situation:

```python
predetermined_answers: dict[str, str] = {
    # If you DO have conflicts:
    "conflicts": "Yes, I will disclose these separately",

    # If you DO need sponsorship:
    "require sponsorship": "Yes",
    "visa sponsorship": "Yes",

    # If you HAVE worked somewhere before:
    "worked here before": "Yes, as an intern in 2023",
}
```

## Future Improvements

Potential enhancements:

1. **Add more patterns** as you encounter new common questions
2. **Make answers configurable** via `.env` file
3. **Track API call savings** in the database
4. **Support regex patterns** for more flexible matching
5. **Add confidence scoring** to distinguish between simple and creative questions

## Summary

✅ **Implemented**: Two-tier answer system  
✅ **Result**: 50-70% reduction in API calls  
✅ **Cost savings**: $3-15/month for typical usage  
✅ **Code quality**: Clean, documented, type-hinted  
✅ **Easy to extend**: Just add patterns to config

The system now intelligently decides when to use OpenAI vs predetermined answers, making it much more cost-efficient while maintaining quality for creative responses.
