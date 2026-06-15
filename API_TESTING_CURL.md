# API Testing with cURL

This guide provides cURL commands to test the evaluation flow manually.

## Setup

### 1. Start the backend
```bash
cd Backend
python run.py
```

### 2. Set environment variables
```bash
export BASE_URL="http://localhost:5000/api"
export CANDIDATE_EMAIL="candidate@test.com"
export CANDIDATE_PASSWORD="password123"
export RECRUITER_EMAIL="recruiter@test.com"
export RECRUITER_PASSWORD="password123"
```

---

## Authentication

### Login as Candidate
```bash
curl -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$CANDIDATE_EMAIL\",
    \"password\": \"$CANDIDATE_PASSWORD\"
  }"
```

**Response:**
```json
{
  "user": {
    "id": 1,
    "email": "candidate@test.com",
    "role": "candidate",
    "candidate": {
      "id": 1,
      "user_id": 1
    }
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "redirect": "/candidate"
}
```

**Save the token:**
```bash
export CANDIDATE_TOKEN="eyJhbGciOiJIUzI1NiIs..."
```

### Login as Recruiter
```bash
curl -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$RECRUITER_EMAIL\",
    \"password\": \"$RECRUITER_PASSWORD\"
  }"
```

**Save the token:**
```bash
export RECRUITER_TOKEN="eyJhbGciOiJIUzI1NiIs..."
```

---

## Candidate Endpoints

### Get All Evaluations
```bash
curl -X GET "$BASE_URL/candidate/evaluations" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN"
```

**Response:**
```json
{
  "evaluations": [
    {
      "id": 1,
      "candidate_id": 1,
      "job_id": 1,
      "score": 85.5,
      "recommendation": "YES",
      "strengths": ["Python", "React"],
      "gaps": ["DevOps"],
      "why_fit": "Strong backend skills...",
      "eval_status": "done",
      "eval_error": null,
      "recruiter_action": "pending",
      "action_taken_at": null,
      "evaluated_at": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-15T10:00:00Z",
      "job": {
        "id": 1,
        "title": "Senior Backend Engineer",
        "company_name": "TechCorp"
      }
    }
  ]
}
```

### Get Single Evaluation (for polling)
```bash
curl -X GET "$BASE_URL/candidate/evaluations/1" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN"
```

**Response:** Same as above, single evaluation object.

### Express Interest in a Job
```bash
curl -X POST "$BASE_URL/jobs/1/express-interest" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN"
```

**Response:** 202 Accepted
```json
{
  "evaluation": {
    "id": 1,
    "candidate_id": 1,
    "job_id": 1,
    "score": null,
    "recommendation": "PENDING",
    "strengths": [],
    "gaps": [],
    "why_fit": null,
    "eval_status": "pending",
    "eval_error": null,
    "recruiter_action": "pending",
    "action_taken_at": null,
    "evaluated_at": null,
    "created_at": "2024-01-15T10:00:00Z",
    "job": {
      "id": 1,
      "title": "Senior Backend Engineer",
      "company_name": "TechCorp"
    }
  }
}
```

### Withdraw Application
```bash
curl -X DELETE "$BASE_URL/candidate/evaluations/1" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN"
```

**Response:** 200 OK
```json
{
  "message": "Withdrawn"
}
```

### Get Feedback Report
```bash
curl -X GET "$BASE_URL/evaluations/1/feedback" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN"
```

**Response:** 200 OK
```json
{
  "candidate_report": "# Your Match Score\n\nYou scored 85/100...",
  "generated_at": "2024-01-15T10:30:00Z"
}
```

---

## Recruiter Endpoints

### Get All Jobs
```bash
curl -X GET "$BASE_URL/jobs" \
  -H "Authorization: Bearer $RECRUITER_TOKEN"
```

**Response:**
```json
{
  "jobs": [
    {
      "id": 1,
      "title": "Senior Backend Engineer",
      "company_name": "TechCorp",
      "location": "Remote",
      "description": "Looking for...",
      "is_active": true,
      "application_count": 5,
      "created_at": "2024-01-15T09:00:00Z"
    }
  ]
}
```

### Get Evaluations for a Job
```bash
curl -X GET "$BASE_URL/evaluations?job_id=1" \
  -H "Authorization: Bearer $RECRUITER_TOKEN"
```

**Response:**
```json
{
  "evaluations": [
    {
      "id": 1,
      "candidate_id": 1,
      "job_id": 1,
      "score": 85.5,
      "recommendation": "YES",
      "recruiter_action": "pending",
      "eval_status": "done",
      "candidate": {
        "id": 1,
        "full_name": "John Doe",
        "email": "john@example.com"
      }
    }
  ],
  "total": 1,
  "job": {
    "id": 1,
    "title": "Senior Backend Engineer"
  }
}
```

### Get Single Evaluation
```bash
curl -X GET "$BASE_URL/evaluations/1" \
  -H "Authorization: Bearer $RECRUITER_TOKEN"
```

**Response:** Same as above, single evaluation object.

### Trigger Evaluation
```bash
curl -X POST "$BASE_URL/evaluate" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"candidate_id\": 1,
    \"job_id\": 1
  }"
```

**Response:** 202 Accepted
```json
{
  "evaluation": {
    "id": 1,
    "eval_status": "pending",
    "recommendation": "PENDING"
  }
}
```

### Take Recruiter Action (Shortlist/Reject)
```bash
curl -X POST "$BASE_URL/recruiter/action" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"candidate_id\": 1,
    \"job_id\": 1,
    \"action\": \"shortlist\"
  }"
```

**Response:** 200 OK
```json
{
  "evaluation": {
    "id": 1,
    "candidate_id": 1,
    "job_id": 1,
    "recruiter_action": "shortlisted",
    "action_taken_at": "2024-01-15T10:35:00Z",
    "score": 85.5,
    "recommendation": "YES"
  }
}
```

**Actions:**
- `"shortlist"` → recruiter_action becomes "shortlisted"
- `"reject"` → recruiter_action becomes "rejected"
- `"reset"` → recruiter_action becomes "pending"

### Alternative: Update Evaluation Action
```bash
curl -X POST "$BASE_URL/evaluations/1/action" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"action\": \"shortlisted\"
  }"
```

**Response:** 200 OK (same as above)

**Actions:**
- `"shortlisted"` → recruiter_action becomes "shortlisted"
- `"rejected"` → recruiter_action becomes "rejected"
- `"pending"` → recruiter_action becomes "pending"

---

## Complete Test Scenario

### 1. Candidate expresses interest
```bash
EVAL_ID=$(curl -s -X POST "$BASE_URL/jobs/1/express-interest" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" | jq -r '.evaluation.id')
echo "Evaluation ID: $EVAL_ID"
```

### 2. Poll for evaluation completion
```bash
for i in {1..30}; do
  STATUS=$(curl -s -X GET "$BASE_URL/candidate/evaluations/$EVAL_ID" \
    -H "Authorization: Bearer $CANDIDATE_TOKEN" | jq -r '.evaluation.eval_status')
  SCORE=$(curl -s -X GET "$BASE_URL/candidate/evaluations/$EVAL_ID" \
    -H "Authorization: Bearer $CANDIDATE_TOKEN" | jq -r '.evaluation.score')
  echo "[$i] Status: $STATUS, Score: $SCORE"
  
  if [ "$STATUS" = "done" ]; then
    echo "Evaluation complete!"
    break
  fi
  
  sleep 2
done
```

### 3. Recruiter shortlists candidate
```bash
curl -X POST "$BASE_URL/recruiter/action" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"candidate_id\": 1,
    \"job_id\": 1,
    \"action\": \"shortlist\"
  }" | jq '.'
```

### 4. Candidate polls for recruiter action
```bash
for i in {1..5}; do
  ACTION=$(curl -s -X GET "$BASE_URL/candidate/evaluations/$EVAL_ID" \
    -H "Authorization: Bearer $CANDIDATE_TOKEN" | jq -r '.evaluation.recruiter_action')
  echo "[$i] Recruiter Action: $ACTION"
  
  if [ "$ACTION" != "pending" ]; then
    echo "Recruiter action received!"
    break
  fi
  
  sleep 1
done
```

### 5. Recruiter rejects candidate
```bash
curl -X POST "$BASE_URL/recruiter/action" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"candidate_id\": 1,
    \"job_id\": 1,
    \"action\": \"reject\"
  }" | jq '.'
```

### 6. Candidate sees rejection
```bash
curl -s -X GET "$BASE_URL/candidate/evaluations/$EVAL_ID" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" | jq '.evaluation.recruiter_action'
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "candidate_id, job_id, action required"
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "error": "Forbidden"
}
```

### 404 Not Found
```json
{
  "error": "Evaluation not found"
}
```

---

## Useful jq Filters

### Extract evaluation ID
```bash
curl -s ... | jq -r '.evaluation.id'
```

### Extract score
```bash
curl -s ... | jq -r '.evaluation.score'
```

### Extract status
```bash
curl -s ... | jq -r '.evaluation.eval_status'
```

### Extract recruiter action
```bash
curl -s ... | jq -r '.evaluation.recruiter_action'
```

### Pretty print JSON
```bash
curl -s ... | jq '.'
```

### Extract all evaluation IDs
```bash
curl -s ... | jq -r '.evaluations[].id'
```

---

## Bash Script for Complete Test

Save as `test_flow.sh`:

```bash
#!/bin/bash

set -e

BASE_URL="http://localhost:5000/api"
CANDIDATE_EMAIL="candidate@test.com"
CANDIDATE_PASSWORD="password123"
RECRUITER_EMAIL="recruiter@test.com"
RECRUITER_PASSWORD="password123"

echo "=== Logging in as candidate ==="
CANDIDATE_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$CANDIDATE_EMAIL\", \"password\": \"$CANDIDATE_PASSWORD\"}")
CANDIDATE_TOKEN=$(echo $CANDIDATE_RESPONSE | jq -r '.access_token')
echo "Candidate token: ${CANDIDATE_TOKEN:0:20}..."

echo "=== Logging in as recruiter ==="
RECRUITER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$RECRUITER_EMAIL\", \"password\": \"$RECRUITER_PASSWORD\"}")
RECRUITER_TOKEN=$(echo $RECRUITER_RESPONSE | jq -r '.access_token')
echo "Recruiter token: ${RECRUITER_TOKEN:0:20}..."

echo "=== Getting jobs ==="
JOBS=$(curl -s -X GET "$BASE_URL/jobs" \
  -H "Authorization: Bearer $RECRUITER_TOKEN")
JOB_ID=$(echo $JOBS | jq -r '.jobs[0].id')
echo "Job ID: $JOB_ID"

echo "=== Candidate expressing interest ==="
EVAL_RESPONSE=$(curl -s -X POST "$BASE_URL/jobs/$JOB_ID/express-interest" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN")
EVAL_ID=$(echo $EVAL_RESPONSE | jq -r '.evaluation.id')
echo "Evaluation ID: $EVAL_ID"

echo "=== Polling for evaluation completion ==="
for i in {1..30}; do
  EVAL=$(curl -s -X GET "$BASE_URL/candidate/evaluations/$EVAL_ID" \
    -H "Authorization: Bearer $CANDIDATE_TOKEN")
  STATUS=$(echo $EVAL | jq -r '.evaluation.eval_status')
  SCORE=$(echo $EVAL | jq -r '.evaluation.score')
  echo "[$i] Status: $STATUS, Score: $SCORE"
  
  if [ "$STATUS" = "done" ]; then
    echo "✓ Evaluation complete!"
    break
  fi
  
  sleep 2
done

echo "=== Recruiter shortlisting candidate ==="
curl -s -X POST "$BASE_URL/recruiter/action" \
  -H "Authorization: Bearer $RECRUITER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"candidate_id\": 1, \"job_id\": $JOB_ID, \"action\": \"shortlist\"}" | jq '.'

echo "=== Candidate polling for recruiter action ==="
for i in {1..5}; do
  EVAL=$(curl -s -X GET "$BASE_URL/candidate/evaluations/$EVAL_ID" \
    -H "Authorization: Bearer $CANDIDATE_TOKEN")
  ACTION=$(echo $EVAL | jq -r '.evaluation.recruiter_action')
  echo "[$i] Recruiter Action: $ACTION"
  
  if [ "$ACTION" != "pending" ]; then
    echo "✓ Recruiter action received!"
    break
  fi
  
  sleep 1
done

echo "=== Test complete ==="
```

Run it:
```bash
chmod +x test_flow.sh
./test_flow.sh
```

---

## Debugging Tips

### Check if backend is running
```bash
curl -s "$BASE_URL/health" | jq '.'
```

### Check authentication
```bash
curl -s "$BASE_URL/me/profile" \
  -H "Authorization: Bearer $CANDIDATE_TOKEN" | jq '.'
```

### Check database state
```bash
# In Python shell
from models import CandidateJobEvaluation
from extensions import db
from app import app

with app.app_context():
    ev = CandidateJobEvaluation.query.first()
    print(f"Status: {ev.eval_status}")
    print(f"Score: {ev.score}")
    print(f"Recruiter Action: {ev.recruiter_action}")
```

### Monitor logs
```bash
tail -f Backend/logs/app.log
```

### Check network requests
```bash
# In browser DevTools, Network tab
# Filter by XHR to see API requests
```
