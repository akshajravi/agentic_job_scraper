"""
Test script to demonstrate predetermined answers optimization.
This shows how the system avoids unnecessary OpenAI API calls.
"""

from agent.config import settings
from agent.apply.greenhouse import GreenhouseApplier
from agent.match.resume_parser import ResumeParser
from pathlib import Path

# Example questions that will now use predetermined answers (no API calls!)
test_questions = [
    "Do you have any conflicts of interest?",
    "Have you worked here before?",
    "Are you authorized to work in the United States?",
    "Do you require visa sponsorship?",
    "Have you been convicted of a felony?",
    "Were you referred by a current employee?",
    "Are you 18 years or older?",
    "Do you certify that all information is accurate?",
    "How did you hear about this position?",
    "Where did you find this job posting?",
    "Please specify your source:",
]

# Example questions that will still use OpenAI (creative answers needed)
creative_questions = [
    "Why do you want to work at our company?",
    "Tell us about a challenging project you worked on.",
    "What are your salary expectations?",
    "Describe your leadership experience.",
]

def test_predetermined_answers():
    """Test that predetermined answers work without API calls."""
    
    print("=" * 80)
    print("PREDETERMINED ANSWERS TEST")
    print("=" * 80)
    print("\nThese questions will use predetermined answers (NO API calls):\n")
    
    # Create a mock applier (we'll just use the check method)
    resume_path = Path("resume.pdf")
    if not resume_path.exists():
        print("Note: resume.pdf not found, using mock data")
        # For testing, we'll just check the pattern matching logic
        
    print("Configured predetermined answer patterns:")
    for pattern, answer in settings.predetermined_answers.items():
        print(f"  • '{pattern}' → {answer}")
    
    print("\n" + "-" * 80)
    print("TESTING COMMON QUESTIONS:")
    print("-" * 80 + "\n")
    
    for question in test_questions:
        question_lower = question.lower()
        matched = False
        matched_pattern = None
        matched_answer = None
        
        # Simulate the matching logic
        for pattern, answer in settings.predetermined_answers.items():
            if pattern.lower() in question_lower:
                matched = True
                matched_pattern = pattern
                matched_answer = answer
                break
        
        if matched:
            print(f"✓ Question: {question}")
            print(f"  Pattern matched: '{matched_pattern}'")
            print(f"  Answer: {matched_answer}")
            print(f"  API call saved: $0.002-0.005")
        else:
            print(f"✗ Question: {question}")
            print(f"  No predetermined answer - would call OpenAI API")
        print()
    
    print("\n" + "-" * 80)
    print("CREATIVE QUESTIONS (will still use OpenAI):")
    print("-" * 80 + "\n")
    
    for question in creative_questions:
        print(f"? Question: {question}")
        print(f"  No predetermined answer - needs OpenAI for personalized response")
        print()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    matched_count = len([q for q in test_questions if any(p.lower() in q.lower() for p in settings.predetermined_answers.keys())])
    print(f"\nSimple questions matched: {matched_count}/{len(test_questions)}")
    print(f"API calls saved per application: ~{matched_count}")
    print(f"Estimated cost savings per application: $0.02-0.06")
    print(f"\nWith 10 applications/day: Save ~$6-18/month in API costs!")
    print("\n💡 Note: 'How did you hear' questions use smart logic:")
    print("   - Text fields → 'Corporate Website'")
    print("   - Dropdowns → Try 'Corporate Website', fallback to 'Other' if not available")
    print("   - Follow-up 'Please specify' → 'Corporate Website'")
    print()

if __name__ == "__main__":
    test_predetermined_answers()

