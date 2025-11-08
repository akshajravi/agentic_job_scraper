# Greenhouse Fake Dropdown Fix

## Problem
Greenhouse uses fake dropdowns - they look like regular select elements but are actually:
- Hidden `<input>` fields (storing the selected value)
- Clickable `<div>` or `<button>` elements (that open a JavaScript menu)
- JavaScript-powered menus with options

When the bot tried to `.fill()` or `.select_option()` on these fields, Greenhouse's validation rejected it because it expected user interaction (clicking the menu option).

## Solution Implemented

### 1. New Method: `_fill_fake_dropdown()`
**Location:** `greenhouse.py` lines 308-464

This method handles fake dropdowns with a 3-step process:

#### Step 1: Find the Clickable Element
Since the actual input is hidden, we need to find the visible clickable element. The method tries multiple Greenhouse patterns:
```python
# Pattern examples:
- Adjacent div: '#field_id + div'
- Div with select class: 'div[id*="field_id"][class*="select"]'
- Role-based: 'div[id*="field_id"][role="combobox"]'
- Parent container patterns
```

#### Step 2: Click to Open Menu
```python
clickable.scroll_into_view_if_needed()
clickable.click()
time.sleep(0.8)  # Wait for menu animation
```

#### Step 3: Find and Click the Option
The method tries multiple strategies:
1. **Exact match** - Multiple selectors for common Greenhouse patterns
2. **Fuzzy match** - If exact fails, searches all visible options for partial matches

```python
# Example selectors tried:
- '[role="option"]:has-text("United States")'
- '[role="listbox"] li:has-text("United States")'
- 'li:has-text("United States")'
```

### 2. Updated Field Filling Logic
**Location:** `greenhouse.py` lines 685-735

The field filling logic now:
1. **Detects** if it's a fake dropdown or real select
```python
tag_name = element.evaluate('el => el.tagName').lower()
is_fake_dropdown = (tag_name == 'input' or input_type == 'hidden')
```

2. **Routes** to appropriate handler:
   - **Fake dropdown** → `_fill_fake_dropdown()` (new click-based method)
   - **Real select** → `element.select_option()` (existing method)

### 3. Improved Detection
**Location:** `greenhouse.py` lines 445-497

Enhanced detection of fake dropdowns:
- Looks for hidden inputs with associated labels
- Marks them as `type: 'select'` with `is_fake_dropdown: True`
- Doesn't try to get options upfront (menu isn't open yet)
- Options are found dynamically when the dropdown is clicked

## Key Features

### Robust Selector Strategy
The implementation tries **multiple selector patterns** because Greenhouse uses different structures across different companies:
- Role-based selectors (`[role="option"]`)
- List-based selectors (`li`, `ul[role="listbox"] > li`)
- Class-based selectors (`.select-option`)
- Data attributes (`[data-option]`)

### Fuzzy Matching Fallback
If exact text match fails, the method searches all visible options and matches:
- Answer contains option text: `"United States" in "United States of America"`
- Option contains answer text: `"US" in "United States"`

### Detailed Logging
Every step is logged for debugging:
```
✓ Found field with id: job_application_answers_123
✓ Found clickable element: div[id*="job_application_answers_123"][role="combobox"]
✓ Clicking dropdown to open menu...
✓ Looking for option: 'United States'
✓ Found option with selector: [role="option"]:has-text("United States")
✓ Successfully selected: United States
```

### Error Handling
- Logs available options if selection fails (helps debugging)
- Full traceback on exceptions
- Graceful fallback to other selectors if one fails

## What Still Works

All existing features remain intact:
- ✅ Predetermined answers (saves API costs)
- ✅ Smart dropdown selection (country, clearance, etc.)
- ✅ Real-time field filling
- ✅ Resume data extraction
- ✅ OpenAI fallback for custom questions
- ✅ Real `<select>` element handling

## Testing

To test the fix:

```bash
# Run a single application test
python test_single_application.py

# Check logs for:
# "Detected fake dropdown, using click method..."
# "Successfully selected: [option]"
```

Look for screenshots in `screenshots/` directory:
- `pre_submit_*.png` - Shows filled form before submission
- `post_submit_*.png` - Shows confirmation page after submission

## Common Greenhouse Dropdown Patterns

### Pattern 1: Hidden Input + Adjacent Div
```html
<input type="hidden" id="job_application_answers_123" />
<div class="select-wrapper">Select...</div>
```

### Pattern 2: Hidden Input with Role Combobox
```html
<input type="hidden" id="field_123" />
<div role="combobox" aria-labelledby="field_123">Select...</div>
```

### Pattern 3: Parent Container
```html
<div class="field-container">
  <input type="hidden" id="field_123" />
  <div class="select-trigger">Select...</div>
</div>
```

All three patterns are now handled by the implementation.

## Next Steps

If you encounter a Greenhouse form where dropdowns still don't work:

1. **Check the logs** - Look for "Could not find option" messages
2. **Check the screenshots** - See if menu is opening
3. **Inspect the HTML** - Look at the dropdown structure
4. **Add new selector pattern** - Update `_fill_fake_dropdown()` with new pattern

The implementation is designed to be extensible - you can add new selector patterns without changing the overall logic.

