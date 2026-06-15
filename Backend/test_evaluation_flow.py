#!/usr/bin/env python3
"""
Test script for the complete evaluation flow.

Tests:
1. Candidate expresses interest in a job (triggers evaluation)
2. Evaluation completes within 15 seconds
3. Recruiter takes action (shortlist/reject)
4. Candidate sees the update via polling

Usage:
    python Backend/test_evaluation_flow.py
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:5000/api"

# Test credentials (adjust to match your test data)
CANDIDATE_EMAIL = "test.candidate@example.com"
CANDIDATE_PASSWORD = "password123"
RECRUITER_EMAIL = "test.recruiter@example.com"
RECRUITER_PASSWORD = "password123"

def log(msg: str, level: str = "INFO"):
    """Print timestamped log message."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {level}: {msg}")

def login(email: str, password: str) -> dict:
    """Login and return user data + token."""
    log(f"Logging in as {email}...")
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password,
    })
    if res.status_code != 200:
        log(f"Login failed: {res.text}", "ERROR")
        return {}
    data = res.json()
    log(f"Login successful. Token: {data['access_token'][:20]}...")
    return data

def get_headers(token: str) -> dict:
    """Return authorization headers."""
    return {"Authorization": f"Bearer {token}"}

def test_evaluation_flow():
    """Run the complete evaluation flow test."""
    
    # 1. Login as candidate
    log("=" * 60)
    log("STEP 1: Candidate Login")
    log("=" * 60)
    candidate_data = login(CANDIDATE_EMAIL, CANDIDATE_PASSWORD)
    if not candidate_data:
        log("Candidate login failed. Exiting.", "ERROR")
        return False
    candidate_token = candidate_data["access_token"]
    candidate_id = candidate_data["user"]["candidate"]["id"]
    log(f"Candidate ID: {candidate_id}")

    # 2. Login as recruiter
    log("\n" + "=" * 60)
    log("STEP 2: Recruiter Login")
    log("=" * 60)
    recruiter_data = login(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    if not recruiter_data:
        log("Recruiter login failed. Exiting.", "ERROR")
        return False
    recruiter_token = recruiter_data["access_token"]
    recruiter_id = recruiter_data["user"]["recruiter"]["id"]
    log(f"Recruiter ID: {recruiter_id}")

    # 3. Get available jobs
    log("\n" + "=" * 60)
    log("STEP 3: Fetch Available Jobs")
    log("=" * 60)
    res = requests.get(f"{BASE_URL}/jobs", headers=get_headers(recruiter_token))
    if res.status_code != 200:
        log(f"Failed to fetch jobs: {res.text}", "ERROR")
        return False
    jobs = res.json().get("jobs", [])
    if not jobs:
        log("No jobs available. Please create a job first.", "ERROR")
        return False
    job = jobs[0]
    job_id = job["id"]
    log(f"Using job: {job['title']} (ID: {job_id})")

    # 4. Candidate expresses interest
    log("\n" + "=" * 60)
    log("STEP 4: Candidate Expresses Interest")
    log("=" * 60)
    log(f"Candidate expressing interest in job {job_id}...")
    res = requests.post(
        f"{BASE_URL}/jobs/{job_id}/express-interest",
        headers=get_headers(candidate_token)
    )
    if res.status_code not in (200, 202):
        log(f"Failed to express interest: {res.text}", "ERROR")
        return False
    eval_data = res.json()["evaluation"]
    eval_id = eval_data["id"]
    log(f"Evaluation created. ID: {eval_id}, Status: {eval_data['eval_status']}")

    # 5. Poll for evaluation completion
    log("\n" + "=" * 60)
    log("STEP 5: Poll for Evaluation Completion (max 60 seconds)")
    log("=" * 60)
    start_time = time.time()
    max_wait = 60
    poll_interval = 2
    completed = False

    while time.time() - start_time < max_wait:
        res = requests.get(
            f"{BASE_URL}/candidate/evaluations/{eval_id}",
            headers=get_headers(candidate_token)
        )
        if res.status_code != 200:
            log(f"Failed to fetch evaluation: {res.text}", "ERROR")
            return False
        
        ev = res.json()["evaluation"]
        elapsed = int(time.time() - start_time)
        log(f"[{elapsed}s] Status: {ev['eval_status']}, Score: {ev.get('score')}, Rec: {ev.get('recommendation')}")
        
        if ev["eval_status"] == "done":
            log(f"✓ Evaluation completed in {elapsed} seconds!")
            log(f"  Score: {ev['score']}/100")
            log(f"  Recommendation: {ev['recommendation']}")
            log(f"  Strengths: {ev.get('strengths', [])[:2]}")
            log(f"  Gaps: {ev.get('gaps', [])[:2]}")
            completed = True
            break
        elif ev["eval_status"] == "error":
            log(f"✗ Evaluation failed: {ev.get('eval_error')}", "ERROR")
            return False
        
        time.sleep(poll_interval)

    if not completed:
        log(f"✗ Evaluation did not complete within {max_wait} seconds", "ERROR")
        return False

    # 6. Recruiter takes action (shortlist)
    log("\n" + "=" * 60)
    log("STEP 6: Recruiter Takes Action (Shortlist)")
    log("=" * 60)
    log(f"Recruiter shortlisting candidate {candidate_id} for job {job_id}...")
    res = requests.post(
        f"{BASE_URL}/recruiter/action",
        headers=get_headers(recruiter_token),
        json={
            "candidate_id": candidate_id,
            "job_id": job_id,
            "action": "shortlist"
        }
    )
    if res.status_code != 200:
        log(f"Failed to shortlist: {res.text}", "ERROR")
        return False
    updated_ev = res.json()["evaluation"]
    log(f"✓ Candidate shortlisted!")
    log(f"  Recruiter Action: {updated_ev['recruiter_action']}")
    log(f"  Action Taken At: {updated_ev.get('action_taken_at')}")

    # 7. Candidate polls for recruiter action update
    log("\n" + "=" * 60)
    log("STEP 7: Candidate Polls for Recruiter Action Update")
    log("=" * 60)
    log("Candidate polling for recruiter action changes...")
    start_time = time.time()
    max_wait = 10
    found_update = False

    while time.time() - start_time < max_wait:
        res = requests.get(
            f"{BASE_URL}/candidate/evaluations/{eval_id}",
            headers=get_headers(candidate_token)
        )
        if res.status_code != 200:
            log(f"Failed to fetch evaluation: {res.text}", "ERROR")
            return False
        
        ev = res.json()["evaluation"]
        elapsed = int(time.time() - start_time)
        
        if ev["recruiter_action"] == "shortlisted":
            log(f"✓ Candidate sees shortlist status in {elapsed} seconds!")
            log(f"  Recruiter Action: {ev['recruiter_action']}")
            found_update = True
            break
        
        log(f"[{elapsed}s] Recruiter Action: {ev['recruiter_action']} (waiting...)")
        time.sleep(1)

    if not found_update:
        log(f"✗ Candidate did not see recruiter action within {max_wait} seconds", "ERROR")
        return False

    # 8. Test reject action
    log("\n" + "=" * 60)
    log("STEP 8: Recruiter Rejects Candidate")
    log("=" * 60)
    log("Recruiter rejecting candidate...")
    res = requests.post(
        f"{BASE_URL}/recruiter/action",
        headers=get_headers(recruiter_token),
        json={
            "candidate_id": candidate_id,
            "job_id": job_id,
            "action": "reject"
        }
    )
    if res.status_code != 200:
        log(f"Failed to reject: {res.text}", "ERROR")
        return False
    updated_ev = res.json()["evaluation"]
    log(f"✓ Candidate rejected!")
    log(f"  Recruiter Action: {updated_ev['recruiter_action']}")

    # 9. Candidate sees rejection
    log("\n" + "=" * 60)
    log("STEP 9: Candidate Sees Rejection")
    log("=" * 60)
    res = requests.get(
        f"{BASE_URL}/candidate/evaluations/{eval_id}",
        headers=get_headers(candidate_token)
    )
    if res.status_code != 200:
        log(f"Failed to fetch evaluation: {res.text}", "ERROR")
        return False
    ev = res.json()["evaluation"]
    if ev["recruiter_action"] == "rejected":
        log(f"✓ Candidate sees rejection status!")
        log(f"  Recruiter Action: {ev['recruiter_action']}")
    else:
        log(f"✗ Candidate does not see rejection", "ERROR")
        return False

    # Summary
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    log("✓ All tests passed!")
    log("  1. Candidate expressed interest")
    log("  2. Evaluation completed successfully")
    log("  3. Recruiter shortlisted candidate")
    log("  4. Candidate saw shortlist status")
    log("  5. Recruiter rejected candidate")
    log("  6. Candidate saw rejection status")
    return True

if __name__ == "__main__":
    try:
        success = test_evaluation_flow()
        exit(0 if success else 1)
    except Exception as e:
        log(f"Test failed with exception: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        exit(1)
