"""
Quick test to verify Prompt 5 implementation.
Run: python test_prompt5.py
"""
import os
import sys

def test_imports():
    """Test that all new modules can be imported."""
    print("Testing imports...")
    try:
        from agents.feedback_agent import generate_feedback_report
        print("✅ feedback_agent imported")
    except ImportError as e:
        print(f"❌ feedback_agent import failed: {e}")
        return False
    
    try:
        from agents.async_agents import run_enrichment_async
        print("✅ async_agents imported")
    except ImportError as e:
        print(f"❌ async_agents import failed: {e}")
        return False
    
    return True


def test_models():
    """Test that FeedbackReport model exists."""
    print("\nTesting models...")
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            from models import FeedbackReport
            print(f"✅ FeedbackReport model exists")
            print(f"   Table: {FeedbackReport.__tablename__}")
            return True
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False


def test_groq_key():
    """Test that GROQ_API_KEY is set."""
    print("\nTesting configuration...")
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        print(f"✅ GROQ_API_KEY is set (length: {len(groq_key)})")
        return True
    else:
        print("⚠️  GROQ_API_KEY not set - pipeline will raise error")
        print("   Set it in Backend/.env: GROQ_API_KEY=gsk_...")
        return False


def test_pipeline_no_mock():
    """Test that pipeline raises error without GROQ_API_KEY."""
    print("\nTesting no-mock enforcement...")
    
    # Temporarily unset GROQ_API_KEY
    original_key = os.getenv("GROQ_API_KEY")
    if "GROQ_API_KEY" in os.environ:
        del os.environ["GROQ_API_KEY"]
    
    try:
        from app import create_app
        from agents import _groq_evaluate
        
        app = create_app()
        with app.app_context():
            try:
                # Create mock candidate and job objects
                class MockUser:
                    full_name = "Test User"
                
                class MockCandidate:
                    user = MockUser()
                    headline = "Test"
                    years_experience = 5
                    skills = ["python"]
                    resume_skills = []
                    summary = "Test summary"
                    github_repos = None
                    lc_easy = None
                
                class MockJob:
                    title = "Test Job"
                    description = "Test description"
                    skills_required = ["python"]
                
                # This should raise ValueError
                result = _groq_evaluate(MockCandidate(), MockJob())
                print("❌ Pipeline did NOT raise error without GROQ_API_KEY")
                return False
            except ValueError as e:
                if "GROQ_API_KEY is required" in str(e):
                    print("✅ Pipeline correctly raises error without GROQ_API_KEY")
                    print(f"   Error message: {str(e)[:80]}...")
                    return True
                else:
                    print(f"❌ Wrong error: {e}")
                    return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original key
        if original_key:
            os.environ["GROQ_API_KEY"] = original_key


def test_async_agents():
    """Test that async agents can be called."""
    print("\nTesting async agents...")
    try:
        import asyncio
        from agents.async_agents import github_agent_async, leetcode_agent_async
        import aiohttp
        
        async def test():
            async with aiohttp.ClientSession() as session:
                # Test with invalid username (should return error, not crash)
                result = await github_agent_async("", session)
                return result == {}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(test())
            if success:
                print("✅ Async agents work correctly")
                return True
            else:
                print("❌ Async agents returned unexpected result")
                return False
        finally:
            loop.close()
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Prompt 5 Implementation Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Models", test_models()))
    results.append(("Configuration", test_groq_key()))
    results.append(("No Mock Enforcement", test_pipeline_no_mock()))
    results.append(("Async Agents", test_async_agents()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Prompt 5 is fully implemented.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
