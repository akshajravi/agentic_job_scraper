# Greenhouse Fake Dropdown Implementation - Summary

## ✅ What We've Accomplished

### 1. **Fake Dropdown Detection & Handling**
Successfully implemented detection and interaction with Greenhouse's custom JavaScript dropdowns that appear as text inputs.

**Key Features:**
- Detects fake dropdowns by checking for `role="combobox"`, `readonly` attributes, and adjacent dropdown indicators
- Uses `aria-controls` attribute to find the correct menu (avoiding confusion with job description text)
- Clicks input field to open dropdown menu
- Finds and clicks options from the menu
- Triggers change/blur/input events to ensure form state updates
- Includes verification logging to confirm selections

### 2. **Success Rate: ~95%**
Out of 21 custom fields detected, **20 are successfully filled**:

✅ **Working Fields:**
- Country* → "United States"
- School* → "Texas A&M University" (searchable dropdown with type-ahead)
- LinkedIn Profile → (filled with OpenAI-generated text)
- Website → (filled with OpenAI-generated text)
- CLEARANCE ELIGIBILITY* → "Yes, I am eligible for a U.S. security clearance"
- Security clearance level → "N/A - have never held U.S. security clearance"
- EXPORT CONTROLS* → "I understand and acknowledge these requirements"
- ~~U.S. WORK AUTHORIZATION*~~ → "Yes" (clicks correctly but may have timing issue - see below)
- Sponsorship* → "No"
- U.S. Person status* → "Yes, I am a U.S. citizen and eligible for security clearance"
- HISTORY WITH ANDURIL* → "No, I have not previously worked for or applied to this company"
- Ever been employed* → "No"
- CONFLICT OF INTEREST* → "No"
- Onsite availability* → "Yes"
- Technical experience* → (OpenAI-generated, fuzzy matched to "Yes")
- How did you hear* → "Google job search"
- If other specify → "Online job board"
- Gender → "Male"
- Hispanic/Latino → "No"
- Veteran Status → "I am not a protected veteran"
- Disability Status → "No, I do not have a disability"

### 3. **Smart Features**

#### **Predetermined Answers** (Saves API costs)
- 18+ patterns matched automatically without OpenAI calls
- Includes clearance, work authorization, demographics, location, etc.
- Customized with user's actual information (gender, ethnicity, veteran/disability status)

#### **Fuzzy Matching**
- Handles case-insensitive matching ("Decline to self-identify" matches "Decline To Self Identify")
- Normalizes punctuation (hyphens, underscores)
- Word-based matching for complex phrases

#### **Searchable Dropdowns**
- Special handling for School/University fields
- Types into the search box instead of clicking through huge lists
- Automatically selects first matching result

#### **Menu-Specific Selection**
- Uses `aria-controls` to target the correct dropdown menu
- Avoids selecting wrong options from job description or other page elements

## 🔍 Known Issues

### **U.S. WORK AUTHORIZATION** - Intermittent Failure
**Status:** Clicks option correctly but validation sometimes fails

**What's happening:**
- Bot successfully finds and clicks "Yes" option
- Change/blur/input events are fired
- But Greenhouse's form validation still reports "Select... This field is required"

**Possible causes:**
1. **Timing issue** - Selection might not persist if form state updates too slowly
2. **React state sync** - Greenhouse uses React, and the state update might not complete before submission
3. **Hidden validation** - There might be additional validation logic we're not triggering

**Current mitigations:**
- Added 0.5s wait after clicking option
- Added 0.3s wait after firing events
- Added verification logging to check field value

**Suggested next steps:**
1. Increase wait times to 1-2 seconds for this specific field
2. Try clicking the option twice to ensure it sticks
3. Use browser DevTools to inspect what events Greenhouse expects
4. Consider using Playwright's `select_option()` if there's a hidden `<select>` element

## 📊 API Cost Savings

**Before optimization:**
- All 21 fields would call OpenAI → $0.50-1.00 per application

**After optimization:**
- Only 3-4 fields call OpenAI (LinkedIn, Website, custom questions)
- ~18 fields use predetermined answers
- **Savings: ~80-85% reduction in API costs**

## 🎯 Code Quality

### **Detection Method** (`_is_fake_dropdown_input`)
Checks for:
- `role="combobox"`
- `aria-haspopup="listbox"`
- `readonly` or `aria-readonly` attributes
- Adjacent dropdown indicators (arrows, buttons)
- Parent containers with "select", "dropdown", "combobox" classes

### **Filling Method** (`_fill_fake_dropdown`)
Process:
1. Find input field by selector
2. Check for special cases (searchable dropdowns like School)
3. Click input field to open menu
4. Find menu using `aria-controls` attribute
5. Try exact match for option text
6. Try fuzzy match if exact fails
7. Click the matching option
8. Wait for dropdown to close
9. Fire change/blur/input events
10. Verify selection with logging

### **Error Handling**
- Graceful degradation if click fails (tries JavaScript click)
- Detailed logging at each step
- Shows available options if selection fails
- Continues to next field even if one fails

## 🚀 Next Steps for Production

1. **Test on more Greenhouse companies** - Different companies may use different dropdown structures
2. **Monitor U.S. WORK AUTHORIZATION** - Watch for validation failures and adjust timing
3. **Add race/ethnicity handling** - Currently defaults to "Asian", could be smarter about "South Asian" vs "Asian"
4. **Handle multi-page forms** - Some Greenhouse forms have multiple pages
5. **Add retry logic** - If validation fails, retry filling the specific failed fields
6. **Screenshot on failure** - Capture state of form when validation fails

## 📝 Testing Checklist

When testing with new jobs:
- [ ] All dropdowns are detected (check for 0 hidden inputs found)
- [ ] Country dropdown works
- [ ] School search works (type-ahead)
- [ ] Work authorization dropdowns work
- [ ] Demographics dropdowns work  
- [ ] Pre-submission screenshot shows all fields filled
- [ ] No validation errors before submit
- [ ] Application successfully submits

## 🎓 Lessons Learned

1. **Greenhouse uses visible text inputs, not hidden inputs** - Initial implementation looked for `input[type="hidden"]` but modern Greenhouse uses `input[type="text"][role="combobox"]`

2. **`aria-controls` is crucial** - Without it, we were finding wrong options from the job description instead of the actual menu

3. **Event triggering is important** - Clicking isn't enough; must fire change/blur/input events for React to update state

4. **Timing matters** - Greenhouse's JavaScript needs time to process selections before moving to the next field

5. **Fuzzy matching is essential** - Option text varies (capitalization, punctuation) so exact string match often fails

## 🔧 Configuration

All predetermined answers are in `agent/config.py`:
- Work authorization: "Yes"
- Sponsorship: "No"
- Clearance: "Yes, I am eligible for a U.S. security clearance"
- Demographics: Male, Asian, Not veteran, No disability
- How did you hear: "Google job search"

Update these based on your actual situation!

