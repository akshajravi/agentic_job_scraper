# API Call Optimization Summary

## Before vs After

### BEFORE (Inefficient) ❌

```
Question: "Do you have any conflicts?"
   ↓
❌ Call OpenAI API ($0.003)
   ↓
Answer: "No"
```

Every question → OpenAI API call → $$$

### AFTER (Optimized) ✅

```
Question: "Do you have any conflicts?"
   ↓
Check predetermined answers
   ↓
✓ Match found: "No"
   ↓
Return "No" (FREE!)
```

```
Question: "Why do you want to work here?"
   ↓
Check predetermined answers
   ↓
✗ No match found
   ↓
🤖 Call OpenAI API ($0.003)
   ↓
Generate personalized answer
```

## Code Changes

### 1. Config (`agent/config.py`)

Added 27 predetermined answer patterns:

- Conflicts of interest: "No"
- Previous employment: "No"
- Work authorization: "Yes"
- Sponsorship needs: "No"
- And more...

### 2. Greenhouse Applier (`agent/apply/greenhouse.py`)

**New method: `_check_predetermined_answer()`**

```python
def _check_predetermined_answer(self, question: str) -> Optional[str]:
    """Check if question matches a predetermined answer pattern."""
    for pattern, answer in settings.predetermined_answers.items():
        if pattern.lower() in question.lower():
            return answer  # Found a match!
    return None  # No match, need OpenAI
```

**Updated method: `_answer_custom_question()`**

```python
def _answer_custom_question(self, question: str, ...):
    # STEP 1: Check predetermined first
    predetermined = self._check_predetermined_answer(question)
    if predetermined:
        return predetermined  # Saved API call!

    # STEP 2: Use OpenAI for creative questions
    return self._call_openai_api(...)
```

## Real-World Impact

### Example Application

Typical job application has:

- 6 simple yes/no questions
- 2 creative free-response questions

**Before:**

- API calls: 8
- Cost: $0.024

**After:**

- API calls: 2 (75% reduction)
- Cost: $0.006
- Savings: $0.018 per application

**Monthly (10 applications/day):**

- Before: ~$7.20
- After: ~$1.80
- **Monthly savings: $5.40**

**Annual:**

- **Savings: ~$65/year**

## Files Modified

1. ✅ `agent/config.py` - Added predetermined_answers dictionary
2. ✅ `agent/apply/greenhouse.py` - Added smart answer selection logic

## How to Customize

Edit the `predetermined_answers` in `agent/config.py`:

```python
predetermined_answers: dict[str, str] = {
    # Add your own patterns:
    "your keyword": "Your Answer",
    "another pattern": "Another Answer",
}
```

**Pattern matching is case-insensitive and substring-based:**

- Pattern `"conflicts"` matches:
  - "Do you have any **conflicts** of interest?"
  - "Any **conflicts** to disclose?"
  - "Business **conflicts**?"

## Testing

Run the test to see it in action:

```bash
python test_predetermined_answers.py
```

Output shows:

- ✓ Questions matched with predetermined answers (saved API calls)
- ? Questions that still need OpenAI
- 💰 Cost savings estimate

## Logs

When running applications, you'll see:

**Predetermined answer used:**

```
INFO: Processing question: Do you have any conflicts of interest?
INFO: ✓ Matched predetermined answer for 'conflicts': No
INFO: Using predetermined answer: No (saved API call)
```

**OpenAI needed:**

```
INFO: Processing question: Why do you want to work here?
INFO: No predetermined answer found - using OpenAI API
INFO: Generated answer via OpenAI (length: 234 chars)
```

## Key Benefits

✅ **Cost savings**: 50-70% reduction in API costs  
✅ **Faster**: No API latency for simple questions  
✅ **Reliable**: Consistent answers for standard questions  
✅ **Maintainable**: Easy to add new patterns  
✅ **Smart**: Still uses OpenAI for creative questions  
✅ **Logged**: Clear visibility into what's happening

## Next Steps

1. ✅ Test with a real application to verify
2. 📝 Add more patterns as you encounter new questions
3. 📊 Monitor API usage to track savings
4. 🔧 Adjust answers if needed for your situation

---

**Bottom line:** Your system is now much smarter about when to use expensive AI vs free predetermined answers! 🎉
