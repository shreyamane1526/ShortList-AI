# Quick Start: Testing the Evaluation Flow

## Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL or SQLite (already configured)
- GROQ_API_KEY set in Backend/.env

## Setup

### 1. Backend Setup

```bash
cd Backend

# Install dependencies (if not already done)
pip install -r requirements.txt

# Ensure .env has GROQ_API_KEY
cat .env | grep GROQ_API_KEY
# If not set, add it:
# echo "GROQ_API_KEY=your_key_here" >> .env

# Start the backend
python run.py
```

Backend should be running on `http://localhost:5000`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies (if not already done)
npm install

# Start the frontend
npm run dev
```

Frontend should be running on `http://localhost:5173` (or similar)

## Manual Testing (5 minutes)

### Step 1: Create Test Accounts

1. **Recruiter Account:**
   - Go to http://localhost:5173/auth
   - Click "Sign Up"
   - Email: `recruiter@test.com`
   - Password: `password123`
   - Role: Recruiter
   - Company: Test Company

2. **Candidate Account:**
   - Go to http://localhost:5173/auth
   - Click "Sign Up"
   - Email: `candidate@test.com`
   - Password: `password123`
   - Role: Candidate

### Step 2: Recruiter Posts a Job

1. Log in as recruiter
2. Go to Dashboard → Post a Job
3. Fill in:
   - Title: "Senior Backend Engineer"
   - Description: "Looking for Python/Node.js expert"
   - Location: "Remote"
   - Tags: "Python, Node.js, PostgreSQL"
4. Click "Post Job"

### Step 3: Candidate Expresses Interest

1. Log out and log in as candidate
2. Go to Jobs or Dashboard
3. Find the job posted by recruiter
4. Click "Express Interest" or "Apply"
5. **Watch the evaluation start** (status should change to "Evaluating...")

### Step 4: Monitor Evaluation Progress

1. Stay on the Applications page
2. Watch the score ring and status badge
3. **Evaluation should complete in 10-30 seconds**
4. When done:
   - Score appears (e.g., 85/100)
   - Recommendation badge shows (YES/NO)
   - "Feedback" button appears

### Step 5: Recruiter Takes Action

1. Log out and log in as recruiter
2. Go to Dashboard → Candidates
3. Find the candidate
4. Click the **green checkmark** (Shortlist) or **red X** (Reject)
5. See the toast notification: "Candidate shortlisted!" or "Candidate rejected"

### Step 6: Candidate Sees Update

1. Log out and log in as candidate
2. Go to Applications
3. **Within 5 seconds**, the status badge should change to "Shortlisted" or "Rejected"
4. The recruiter action is now visible

## Automated Testing (2 minutes)

### Run the Test Script

```bash
cd Backend
python test_evaluation_flow.py
```

**What it does:**
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
[10:30:45] INFO: Logging in as candidate@test.com...
[10:30:45] INFO: Login successful. Token: eyJhbGciOiJIUzI1NiIs...
[10:30:46] INFO: Candidate ID: 1

[10:30:46] INFO: ============================================================
[10:30:46] INFO: STEP 2: Recruiter Login
[10:30:46] INFO: ============================================================
[10:30:46] INFO: Logging in as recruiter@test.com...
[10:30:46] INFO: Login successful. Token: eyJhbGciOiJIUzI1NiIs...
[10:30:47] INFO: Recruiter ID: 1

[10:30:47] INFO: ============================================================
[10:30:47] INFO: STEP 3: Fetch Available Jobs
[10:30:47] INFO: ============================================================
[10:30:47] INFO: Using job: Senior Backend Engineer (ID: 1)

[10:30:47] INFO: ============================================================
[10:30:47] INFO: STEP 4: Candidate Expresses Interest
[10:30:47] INFO: ============================================================
[10:30:47] INFO: Candidate expressing interest in job 1...
[10:30:47] INFO: Evaluation created. ID: 1, Status: pending

[10:30:47] INFO: ============================================================
[10:30:47] INFO: STEP 5: Poll for Evaluation Completion (max 60 seconds)
[10:30:47] INFO: ============================================================
[10:30:49] INFO: [2s] Status: running, Score: None, Rec: PENDING
[10:30:51] INFO: [4s] Status: running, Score: None, Rec: PENDING
[10:30:53] INFO: [6s] Status: running, Score: None, Rec: PENDING
[10:31:05] INFO: [18s] Status: done, Score: 85.5, Rec: YES
[10:31:05] INFO: ✓ Evaluation completed in 18 seconds!
[10:31:05] INFO:   Score: 85.5/100
[10:31:05] INFO:   Recommendation: YES
[10:31:05] INFO:   Strengths: ['Python expertise', 'PostgreSQL knowledge']
[10:31:05] INFO:   Gaps: ['DevOps experience']

[10:31:05] INFO: ============================================================
[10:31:05] INFO: STEP 6: Recruiter Takes Action (Shortlist)
[10:31:05] INFO: ============================================================
[10:31:05] INFO: Recruiter shortlisting candidate 1 for job 1...
[10:31:06] INFO: ✓ Candidate shortlisted!
[10:31:06] INFO:   Recruiter Action: shortlisted
[10:31:06] INFO:   Action Taken At: 2024-01-15T10:31:06Z

[10:31:06] INFO: ============================================================
[10:31:06] INFO: STEP 7: Candidate Polls for Recruiter Action Update
[10:31:06] INFO: ============================================================
[10:31:06] INFO: Candidate polling for recruiter action changes...
[10:31:07] INFO: [1s] Recruiter Action: shortlisted (waiting...)
[10:31:07] INFO: ✓ Candidate sees shortlist status in 1 seconds!
[10:31:07] INFO:   Recruiter Action: shortlisted

[10:31:07] INFO: ============================================================
[10:31:07] INFO: STEP 8: Recruiter Rejects Candidate
[10:31:07] INFO: ============================================================
[10:31:07] INFO: Recruiter rejecting candidate...
[10:31:08] INFO: ✓ Candidate rejected!
[10:31:08] INFO:   Recruiter Action: rejected

[10:31:08] INFO: ============================================================
[10:31:08] INFO: STEP 9: Candidate Sees Rejection
[10:31:08] INFO: ============================================================
[10:31:08] INFO: ✓ Candidate sees rejection status!
[10:31:08] INFO:   Recruiter Action: rejected

[10:31:08] INFO: ============================================================
[10:31:08] INFO: TEST SUMMARY
[10:31:08] INFO: ============================================================
[10:31:08] INFO: ✓ All tests passed!
[10:31:08] INFO:   1. Candidate expressed interest
[10:31:08] INFO:   2. Evaluation completed successfully
[10:31:08] INFO:   3. Recruiter shortlisted candidate
[10:31:08] INFO:   4. Candidate saw shortlist status
[10:31:08] INFO:   5. Recruiter rejected candidate
[10:31:08] INFO:   6. Candidate saw rejection status
```

## Troubleshooting

### "Evaluation never completes"

**Check:**
1. Backend logs for errors
2. GROQ_API_KEY is set: `echo $GROQ_API_KEY`
3. Network connectivity to Groq API
4. Database is running

**Fix:**
```bash
# Check logs
tail -f Backend/logs/app.log

# Verify GROQ_API_KEY
cat Backend/.env | grep GROQ_API_KEY

# Restart backend
python Backend/run.py
```

### "Recruiter action buttons don't work"

**Check:**
1. Browser console for errors (F12)
2. Network tab to see API response
3. Backend logs for 403/404 errors

**Fix:**
```bash
# Check that recruiter owns the job
# In Backend, run:
python -c "
from models import Job, Recruiter
from extensions import db
from app import app
with app.app_context():
    job = Job.query.first()
    recruiter = Recruiter.query.first()
    print(f'Job recruiter_id: {job.recruiter_id}')
    print(f'Recruiter id: {recruiter.id}')
    print(f'Match: {job.recruiter_id == recruiter.id}')
"
```

### "Candidate doesn't see recruiter action"

**Check:**
1. Polling is running (check Network tab, should see requests every 5 seconds)
2. Notification was created in database
3. Evaluation was updated in database

**Fix:**
```bash
# Check database
python -c "
from models import CandidateJobEvaluation, Notification
from extensions import db
from app import app
with app.app_context():
    ev = CandidateJobEvaluation.query.first()
    print(f'Evaluation recruiter_action: {ev.recruiter_action}')
    print(f'Action taken at: {ev.action_taken_at}')
    notif = Notification.query.filter_by(type='shortlisted').first()
    print(f'Notification created: {notif is not None}')
"
```

## Performance Metrics

**Expected times:**
- Evaluation completion: 10-30 seconds
- Recruiter action update: < 1 second
- Candidate sees recruiter action: < 5 seconds (polling interval)

**If slower:**
1. Check network latency
2. Check Groq API response time
3. Check database query performance
4. Consider reducing polling intervals

## Next Steps

1. **Deploy to production:**
   - Set GROQ_API_KEY in production environment
   - Configure database for production
   - Set up monitoring and logging
   - Test with real users

2. **Optimize for scale:**
   - Consider WebSocket for real-time updates
   - Implement evaluation queue (Celery/RQ)
   - Add caching layer
   - Monitor background thread performance

3. **Add features:**
   - Batch evaluation
   - Evaluation history
   - Partial results
   - Retry logic
   - Timeout handling

## Support

For issues:
1. Check logs: `Backend/logs/app.log` or browser console
2. Run test script: `python Backend/test_evaluation_flow.py`
3. Check environment variables: `echo $GROQ_API_KEY`
4. Verify database: `python Backend/check_db.py`
