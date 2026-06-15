#!/usr/bin/env python3
"""
Test script to verify the voice interview integration works correctly.
"""

import sys
import os
sys.path.append('Backend')
sys.path.append('real_voice_bot')

def test_real_voice_bot_import():
    """Test that we can import real_voice_bot modules."""
    try:
        from real_voice_bot.nodes.utils import load_questions_for_trade
        print("✓ Successfully imported real_voice_bot.nodes.utils")
        
        # Test loading questions
        questions = load_questions_for_trade("Electrician")
        print(f"✓ Loaded {len(questions)} questions for Electrician")
        
        if questions:
            print(f"  Sample question: {questions[0]['question']}")
            print(f"  Focus area: {questions[0]['topic']}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to import real_voice_bot: {e}")
        return False

def test_api_functions():
    """Test the API helper functions."""
    try:
        # Set up Flask app context
        os.chdir('Backend')
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from api import _generate_interview_questions, _assess_interview_answer
            
            # Test question generation
            job_context = {"title": "Electrician", "description": "Electrical work"}
            candidate_context = {"name": "Test User", "years_experience": 5}
            
            questions = _generate_interview_questions(job_context, candidate_context, [])
            print(f"✓ Generated {len(questions)} interview questions")
            
            if questions:
                print(f"  Sample question: {questions[0]['question']}")
                
                # Test answer assessment
                assessment = _assess_interview_answer(
                    questions[0], 
                    "I have 5 years of experience working with electrical systems and always follow safety protocols.",
                    candidate_context
                )
                print(f"✓ Generated assessment with score: {assessment['score']}")
                print(f"  Sentiment: {assessment['sentiment']}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to test API functions: {e}")
        return False

def test_database_model():
    """Test that the CandidateInterview model works."""
    try:
        os.chdir('Backend')
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from models import CandidateInterview
            from extensions import db
            
            # Check if table exists
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'candidate_interviews' in tables:
                print("✓ CandidateInterview table exists in database")
                
                # Check columns
                columns = [col['name'] for col in inspector.get_columns('candidate_interviews')]
                expected_columns = ['id', 'candidate_id', 'evaluation_id', 'transcript', 'overall_score']
                
                for col in expected_columns:
                    if col in columns:
                        print(f"  ✓ Column '{col}' exists")
                    else:
                        print(f"  ✗ Column '{col}' missing")
                        return False
            else:
                print("✗ CandidateInterview table not found")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Failed to test database model: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Voice Interview Integration")
    print("=" * 50)
    
    tests = [
        ("Real Voice Bot Import", test_real_voice_bot_import),
        ("API Functions", test_api_functions),
        ("Database Model", test_database_model),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    for i, (test_name, _) in enumerate(tests):
        status = "PASS" if results[i] else "FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results)
    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
    
    if all_passed:
        print("\n🎉 Voice interview integration is ready!")
        print("\nNext steps:")
        print("1. Start the backend: cd Backend && python run.py")
        print("2. Start the frontend: cd frontend && npm run dev")
        print("3. Navigate to a candidate evaluation and click 'Start Interview'")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())