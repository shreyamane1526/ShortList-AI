# Application Flow Fix: Evaluation + Recruiter Actions + Real-time Updates

## Overview

This document describes the complete fix for the application/evaluation flow, including:
- Reliable background evaluation tasks
- Recruiter action endpoints (shortlist/reject)
- Real-time polling for candidates
- Real-time updates for recruiters

## Architecture

### Backend Flow

```
1. Candidate expresses interest in job
   ↓
2. POST /jobs/{job_id}/express-interest
   ↓
3. CandidateJobEvaluation created with status='pending'
   ↓
4. Background thread spawned (evaluate_candidate_for_job_async)
   ↓
5. _run_job_evaluation() runs in thread:
   - Sets status='running'
   - Calls run_pipeline() (Groq LLM evaluation)
   - Updates score, recommendation, strengths, gaps, why_fit
   - Sets status='done' or 'error'
   - Generates FeedbackReport
   ↓
6. Candidate polls GET /candidate/evaluations/{eval_id}
   - Sees status='done' when complete
   - Displays score and recommendation
   ↓
7. Recruiter takes action: POST /recruiter/action
   - Updates recruiter_action to 'shortlisted' or 'rejected'
   - Creates Notification for candidate
   ↓
8. Candidate polls and sees recruiter_action change
   - Updates badge in UI
```

### Frontend Flow

**Candidate Side:**
- Initial load: Fetch all evaluations
- Pending evaluations: Poll every 2 seconds for status changes
- All evaluations: Poll every 5 seconds for recruiter_action changes
- Stop polling when status='done' or 'error'

**Recruiter Side:**
- Fetch candidates and their latest evaluations
- Click "Shortlist" or "Reject" button
- Button shows loading state
- On success, update local state and show toast
- Refresh candidates list to show updated status

## API Endpoints

### Candidate Endpoints

#### GET /api/candidate/evaluations
Fetch all evaluations for the logged-in candidate.

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

#### GET /api/candidate/evaluations/{eval_id}
Fetch a single evaluation (used for polling).

**Response:** Same as above, single evaluation object.

#### POST /api/jobs/{job_id}/express-interest
Candidate expresses interest in a job (triggers evaluation).

**Response:** 202 Accepted with evaluation object.

#### DELETE /api/candidate/evaluations/{eval_id}
Withdraw an application.

**Response:** 200 OK

### Recruiter Endpoints

#### POST /api/recruiter/action
Update recruiter action for a candidate-job evaluation.

**Request:**
```json
{
  "candidate_id": 1,
  "job_id": 1,
  "action": "shortlist" | "reject" | "reset"
}
```

**Response:** 200 OK with updated evaluation object
```json
{
  "evaluation": {
    "id": 1,
    "recruiter_action": "shortlisted",
    "action_taken_at": "2024-01-15T10:35:00Z",
    ...
  }
}
```

**Status Codes:**
- 200: Success
- 400: Invalid request (missing fields, invalid action)
- 403: Forbidden (not recruiter, wrong job)
- 404: Evaluation not found

#### POST /api/evaluations/{eval_id}/action
Alternative endpoint to update recruiter action (legacy).

**Request:**
```json
{
  "action": "shortlisted" | "rejected" | "pending"
}
```

#### GET /api/evaluations/{eval_id}
Get evaluation details (recruiter only).

#### GET /api/evaluations?job_id={job_id}
List evaluations for a job (recruiter only).

## Database Schema

### CandidateJobEvaluation Table

```sql
CREATE TABLE candidate_job_evaluations (
  id INTEGER PRIMARY KEY,
  candidate_id INTEGER NOT NULL,
  job_id INTEGER NOT NULL,
  
  -- AI Pipeline Outputs
  score FLOAT,                          -- 0-100
  recommendation VARCHAR(16),           -- YES / NO / PENDING
  strengths JSON,                       -- ["skill1", "skill2"]
  gaps JSON,                            -- ["gap1", "gap2"]
  why_fit TEXT,                         -- Explanation
  eval_status VARCHAR(32),              -- pending / running / done / error
  eval_error TEXT,                      -- Error message if failed
  
  -- Recruiter Human-in-the-Loop
  recruiter_action VARCHAR(32),         -- pending / shortlisted / rejected
  action_taken_at DATETIME,             -- When recruiter took action
  evaluated_at DATETIME,                -- When evaluation completed
  
  created_at DATETIME,
  updated_at DATETIME,
  
  UNIQUE(candidate_id, job_id),
  FOREIGN KEY(candidate_id) REFERENCES candidates(id),
  FOREIGN KEY(job_id) REFERENCES jobs(id)
);
```

All fields are already present in the current schema. No migration needed.

## Implementation Details

### Backend Changes

#### 1. agents/__init__.py
- Added `get_task_status()` function for monitoring background tasks
- `_run_job_evaluation()` already handles:
  - Setting status='running'
  - Calling run_pipeline()
  - Updating evaluation with results
  - Generating FeedbackReport
  - Setting status='done' or 'error'
  - Logging errors

#### 2. Backend/api.py
- **POST /recruiter/action**: Fixed to return 200 on success (was missing return code)
  - Validates candidate_id, job_id, action
  - Updates recruiter_action and action_taken_at
  - Creates notification for candidate
  - Returns updated evaluation
  
- **GET /candidate/evaluations/{eval_id}**: Added explicit 200 status code for polling

### Frontend Changes

#### 1. frontend/src/pages/candidate/Applications.tsx
- **Improved polling strategy:**
  - Individual 2-second polls for pending evaluations
  - Separate 5-second polls for recruiter_action changes
  - Stops polling when evaluation completes
  - Shows error state if evaluation fails
  
- **Better UX:**
  - Toast notifications on completion/error
  - Error messages displayed in expanded view
  - Loading spinner while evaluating
  - Feedback button only shows when done

#### 2. frontend/src/pages/recruiter/Candidates.tsx
- **Action buttons:**
  - Shortlist/Reject buttons toggle state
  - Show loading spinner while updating
  - Refresh candidates list after action
  - Toast notifications on success/error
  - Update detail modal if open

## Testing

### Manual Testing

1. **Start the backend:**
   ```bash
   cd Backend
   python run.py
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test the flow:**
   - Create a recruiter account and post a job
   - Create a candidate account
   - Candidate: Express interest in the job
   - Watch the evaluation progress (should complete in 10-30 seconds)
   - Recruiter: Shortlist or reject the candidate
   - Candidate: See the recruiter action update in real-time

### Automated Testing

Run the test script:
```bash
cd Backend
python test_evaluation_flow.py
```

This script:
1. Logs in as candidate and recruiter
2. Candidate expresses interest in a job
3. Polls for evaluation completion (max 60 seconds)
4. Recruiter shortlists the candidate
5. Candidate polls for recruiter action update
6. Recruiter rejects the candidate
7. Candidate sees rejection

**Expected output:**
```
[10:30:45] INFO: ============================================================
[10:30:45] INFO: STEP 1: Candidate Login
[10:30:45] INFO: ============================================================
[10:30:45] INFO: Logging in as test.candidate@example.com...
[10:30:45] INFO: Login successful. Token: eyJhbGciOiJIUzI1NiIs...
...
[10:31:15] INFO: ✓ Evaluation completed in 30 seconds!
[10:31:15] INFO:   Score: 85.5/100
[10:31:15] INFO:   Recommendation: YES
...
[10:31:20] INFO: ✓ All tests passed!
```

## Troubleshooting

### Evaluation Never Completes

**Symptoms:** Status stays 'pending' or 'running' forever

**Causes:**
1. GROQ_API_KEY not set
2. Background thread crashed silently
3. Database connection issue

**Fix:**
1. Check Backend/.env has GROQ_API_KEY set
2. Check Backend logs for errors
3. Verify database is running and accessible
4. Check that run_pipeline() is being called

### Recruiter Action Not Updating

**Symptoms:** Shortlist/Reject buttons don't work

**Causes:**
1. Wrong evaluation ID
2. Recruiter doesn't own the job
3. API endpoint not returning 200

**Fix:**
1. Check browser console for API errors
2. Verify recruiter owns the job
3. Check Backend logs for 403/404 errors

### Candidate Doesn't See Recruiter Action

**Symptoms:** Candidate polls but doesn't see shortlist/reject status

**Causes:**
1. Polling interval too long
2. Notification not created
3. Database not committed

**Fix:**
1. Check polling interval (should be 5 seconds)
2. Verify notification was created in DB
3. Check that db.session.commit() was called

## Performance Considerations

### Polling Intervals
- **Pending evaluations:** 2 seconds (aggressive, evaluation usually completes in 10-30s)
- **Recruiter actions:** 5 seconds (less aggressive, changes are less frequent)
- **Stops polling:** When evaluation completes or errors

### Database Queries
- Each poll makes 1 GET request
- Worst case: 30 pending evaluations × 2-second interval = 15 requests/second
- Acceptable for small deployments; consider WebSocket for scale

### Optimization Ideas
1. **WebSocket:** Real-time updates instead of polling
2. **Server-Sent Events (SSE):** One-way push from server
3. **Batch polling:** Fetch all evaluations in one request
4. **Caching:** Cache evaluation status on client for 1 second

## Future Improvements

1. **WebSocket Support:** Real-time updates without polling
2. **Batch Evaluation:** Evaluate multiple candidates at once
3. **Evaluation Queue:** Use Celery/RQ for better task management
4. **Timeout Handling:** Automatic timeout after 60 seconds
5. **Retry Logic:** Retry failed evaluations automatically
6. **Evaluation History:** Track all evaluation attempts
7. **Partial Results:** Show partial results while evaluation is running

## Files Modified

1. `Backend/agents/__init__.py` - Added task status tracking
2. `Backend/api.py` - Fixed recruiter action endpoint
3. `frontend/src/pages/candidate/Applications.tsx` - Improved polling
4. `frontend/src/pages/recruiter/Candidates.tsx` - Better action handling

## Files Created

1. `Backend/test_evaluation_flow.py` - Comprehensive test script
2. `EVALUATION_FLOW_FIX.md` - This documentation

## Deployment Checklist

- [ ] GROQ_API_KEY is set in Backend/.env
- [ ] Database migrations are up to date
- [ ] Backend is running (python run.py)
- [ ] Frontend is running (npm run dev)
- [ ] Test script passes (python test_evaluation_flow.py)
- [ ] Manual testing completed
- [ ] Polling intervals are appropriate for your scale
- [ ] Error handling is working (check logs)
- [ ] Notifications are being sent
- [ ] Toast messages appear on frontend

## Support

For issues or questions:
1. Check the logs: `Backend/logs/` or browser console
2. Run the test script to isolate the problem
3. Check that all required environment variables are set
4. Verify database schema is correct
5. Check that background threads are running
