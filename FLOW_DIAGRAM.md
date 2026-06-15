# Application Flow Diagram

## Complete Evaluation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CANDIDATE SIDE                                       │
└─────────────────────────────────────────────────────────────────────────────┘

1. CANDIDATE EXPRESSES INTEREST
   ┌──────────────────────────────────────────────────────────────────────┐
   │ Candidate clicks "Express Interest" on job                           │
   │                                                                      │
   │ POST /jobs/{job_id}/express-interest                                │
   │ ├─ Creates CandidateJobEvaluation                                   │
   │ │  ├─ status = 'pending'                                            │
   │ │  ├─ recruiter_action = 'pending'                                  │
   │ │  └─ score = null                                                  │
   │ │                                                                    │
   │ ├─ Spawns background thread                                         │
   │ │  └─ evaluate_candidate_for_job_async()                            │
   │ │                                                                    │
   │ └─ Returns 202 Accepted                                             │
   │    └─ Evaluation object with status='pending'                       │
   └──────────────────────────────────────────────────────────────────────┘

2. BACKGROUND EVALUATION (in thread)
   ┌──────────────────────────────────────────────────────────────────────┐
   │ _run_job_evaluation() runs in daemon thread                          │
   │                                                                      │
   │ ├─ Sets status = 'running'                                          │
   │ │  └─ Commits to DB                                                 │
   │ │                                                                    │
   │ ├─ Calls run_pipeline(candidate_id, job_id)                         │
   │ │  ├─ Loads candidate and job from DB                               │
   │ │  ├─ Calls Groq LLM API                                            │
   │ │  └─ Returns: score, recommendation, strengths, gaps, why_fit      │
   │ │                                                                    │
   │ ├─ Updates CandidateJobEvaluation                                   │
   │ │  ├─ score = 85.5                                                  │
   │ │  ├─ recommendation = 'YES'                                        │
   │ │  ├─ strengths = ['Python', 'React']                               │
   │ │  ├─ gaps = ['DevOps']                                             │
   │ │  ├─ why_fit = 'Strong backend skills...'                          │
   │ │  ├─ evaluated_at = now()                                          │
   │ │  └─ status = 'done'                                               │
   │ │                                                                    │
   │ ├─ Generates FeedbackReport                                         │
   │ │  ├─ candidate_report (markdown)                                   │
   │ │  ├─ recruiter_summary (markdown)                                  │
   │ │  ├─ interview_questions (array)                                   │
   │ │  └─ fairness_assessment (text)                                    │
   │ │                                                                    │
   │ └─ Commits all changes to DB                                        │
   │    └─ If error: status = 'error', eval_error = message             │
   └──────────────────────────────────────────────────────────────────────┘

3. CANDIDATE POLLS FOR EVALUATION (every 2 seconds)
   ┌──────────────────────────────────────────────────────────────────────┐
   │ Frontend: Applications.tsx                                           │
   │                                                                      │
   │ useEffect(() => {                                                   │
   │   const pending = evaluations.filter(e =>                           │
   │     e.eval_status === 'pending' || e.eval_status === 'running'      │
   │   )                                                                  │
   │                                                                      │
   │   pending.forEach(ev => {                                           │
   │     const interval = setInterval(async () => {                      │
   │       const res = await api.get(                                    │
   │         `/candidate/evaluations/${ev.id}`                           │
   │       )                                                              │
   │       const updated = res.data.evaluation                           │
   │                                                                      │
   │       // Update state                                               │
   │       setEvaluations(prevEvals =>                                   │
   │         prevEvals.map(e =>                                          │
   │           e.id === updated.id ? updated : e                         │
   │         )                                                            │
   │       )                                                              │
   │                                                                      │
   │       // If done, stop polling                                      │
   │       if (updated.eval_status === 'done') {                         │
   │         toast.success('Evaluation complete!')                       │
   │         clearInterval(interval)                                     │
   │       }                                                              │
   │     }, 2000) // Poll every 2 seconds                                │
   │   })                                                                │
   │ }, [evaluations])                                                   │
   │                                                                      │
   │ GET /candidate/evaluations/{eval_id}                                │
   │ ├─ Returns 200 OK                                                   │
   │ └─ Evaluation object with updated status and score                  │
   └──────────────────────────────────────────────────────────────────────┘

4. CANDIDATE SEES EVALUATION RESULTS
   ┌──────────────────────────────────────────────────────────────────────┐
   │ UI Updates:                                                          │
   │ ├─ Score ring shows 85/100                                          │
   │ ├─ Recommendation badge shows "YES"                                 │
   │ ├─ Strengths and gaps displayed                                     │
   │ ├─ "Feedback" button appears                                        │
   │ └─ Polling stops                                                    │
   └──────────────────────────────────────────────────────────────────────┘

5. CANDIDATE POLLS FOR RECRUITER ACTION (every 5 seconds)
   ┌──────────────────────────────────────────────────────────────────────┐
   │ Frontend: Applications.tsx                                           │
   │                                                                      │
   │ useEffect(() => {                                                   │
   │   const actionPollInterval = setInterval(                           │
   │     fetchEvaluations,  // Fetch all evaluations                     │
   │     5000  // Every 5 seconds                                        │
   │   )                                                                  │
   │   return () => clearInterval(actionPollInterval)                    │
   │ }, [fetchEvaluations])                                              │
   │                                                                      │
   │ GET /candidate/evaluations                                          │
   │ ├─ Returns 200 OK                                                   │
   │ └─ All evaluations with updated recruiter_action                    │
   └──────────────────────────────────────────────────────────────────────┘

6. CANDIDATE SEES RECRUITER ACTION
   ┌──────────────────────────────────────────────────────────────────────┐
   │ When recruiter_action changes from 'pending' to 'shortlisted':       │
   │ ├─ Badge updates to "Shortlisted"                                   │
   │ ├─ Badge color changes to green                                     │
   │ └─ Toast notification appears                                       │
   │                                                                      │
   │ When recruiter_action changes from 'pending' to 'rejected':          │
   │ ├─ Badge updates to "Rejected"                                      │
   │ ├─ Badge color changes to red                                       │
   │ └─ Toast notification appears                                       │
   └──────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         RECRUITER SIDE                                       │
└─────────────────────────────────────────────────────────────────────────────┘

1. RECRUITER VIEWS CANDIDATES
   ┌──────────────────────────────────────────────────────────────────────┐
   │ Recruiter goes to Dashboard → Candidates                             │
   │                                                                      │
   │ GET /candidates                                                      │
   │ ├─ Returns list of all candidates                                    │
   │ ├─ Each candidate has latest_evaluation                              │
   │ │  ├─ score (if evaluation done)                                     │
   │ │  ├─ recommendation                                                 │
   │ │  └─ recruiter_action (pending/shortlisted/rejected)                │
   │ └─ Returns 200 OK                                                    │
   └──────────────────────────────────────────────────────────────────────┘

2. RECRUITER TAKES ACTION
   ┌──────────────────────────────────────────────────────────────────────┐
   │ Recruiter clicks "Shortlist" or "Reject" button                      │
   │                                                                      │
   │ POST /recruiter/action                                               │
   │ {                                                                    │
   │   "candidate_id": 1,                                                 │
   │   "job_id": 1,                                                       │
   │   "action": "shortlist" | "reject" | "reset"                         │
   │ }                                                                    │
   │                                                                      │
   │ Backend:                                                             │
   │ ├─ Validates all fields                                              │
   │ ├─ Checks recruiter owns the job                                     │
   │ ├─ Updates CandidateJobEvaluation                                    │
   │ │  ├─ recruiter_action = 'shortlisted' | 'rejected' | 'pending'      │
   │ │  └─ action_taken_at = now()                                        │
   │ │                                                                    │
   │ ├─ Creates Notification for candidate                                │
   │ │  ├─ type = 'shortlisted' | 'status_changed'                        │
   │ │  ├─ title = "You've been shortlisted for..."                       │
   │ │  └─ body = "A recruiter shortlisted you for..."                    │
   │ │                                                                    │
   │ ├─ Commits all changes                                               │
   │ └─ Returns 200 OK with updated evaluation                            │
   │                                                                      │
   │ Frontend:                                                            │
   │ ├─ Button shows loading spinner                                      │
   │ ├─ On success:                                                       │
   │ │  ├─ Toast: "Candidate shortlisted!"                                │
   │ │  ├─ Refresh candidates list                                        │
   │ │  └─ Update detail modal if open                                    │
   │ └─ On error:                                                         │
   │    └─ Toast: error message                                           │
   └──────────────────────────────────────────────────────────────────────┘

3. RECRUITER SEES UPDATED STATUS
   ┌──────────────────────────────────────────────────────────────────────┐
   │ Candidates table updates:                                            │
   │ ├─ Status badge changes to "Shortlisted" (green)                     │
   │ ├─ Status badge changes to "Rejected" (red)                          │
   │ └─ Button state updates                                              │
   └──────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE UPDATES                                        │
└─────────────────────────────────────────────────────────────────────────────┘

CandidateJobEvaluation Table:

Initial State (after express interest):
┌────┬──────────────┬────────┬───────┬────────────────┬──────────────┐
│ id │ candidate_id │ job_id │ score │ eval_status    │ recruiter_action │
├────┼──────────────┼────────┼───────┼────────────────┼──────────────┤
│ 1  │ 1            │ 1      │ NULL  │ pending        │ pending      │
└────┴──────────────┴────────┴───────┴────────────────┴──────────────┘

After Evaluation Completes:
┌────┬──────────────┬────────┬───────┬────────────────┬──────────────┐
│ id │ candidate_id │ job_id │ score │ eval_status    │ recruiter_action │
├────┼──────────────┼────────┼───────┼────────────────┼──────────────┤
│ 1  │ 1            │ 1      │ 85.5  │ done           │ pending      │
└────┴──────────────┴────────┴───────┴────────────────┴──────────────┘

After Recruiter Shortlists:
┌────┬──────────────┬────────┬───────┬────────────────┬──────────────┐
│ id │ candidate_id │ job_id │ score │ eval_status    │ recruiter_action │
├────┼──────────────┼────────┼───────┼────────────────┼──────────────┤
│ 1  │ 1            │ 1      │ 85.5  │ done           │ shortlisted  │
└────┴──────────────┴────────┴───────┴────────────────┴──────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                      TIMING DIAGRAM                                          │
└─────────────────────────────────────────────────────────────────────────────┘

Time    Candidate                  Backend                    Recruiter
────────────────────────────────────────────────────────────────────────────
0s      Express Interest ──────────→ Create Evaluation
                                    Spawn Thread
                                    ├─ Set status='running'
                                    └─ Call Groq API

2s      Poll (status=running)
        ←────────────────────────── Return status='running'

4s      Poll (status=running)
        ←────────────────────────── Return status='running'

10s     Poll (status=running)
        ←────────────────────────── Return status='running'

15s                                 Groq API returns
                                    ├─ score=85.5
                                    ├─ recommendation=YES
                                    └─ Set status='done'

17s     Poll (status=done)
        ←────────────────────────── Return status='done'
        Show Score & Recommendation
        Start 5s polling for action

20s                                                           View Candidates
                                                              See evaluation

22s                                                           Click Shortlist
                                                              ──────────────→
                                                              Update recruiter_action
                                                              Create Notification
                                                              ←────────────────
                                                              Show Toast

25s     Poll (recruiter_action=shortlisted)
        ←────────────────────────── Return recruiter_action='shortlisted'
        Update Badge to "Shortlisted"
        Show Toast


┌─────────────────────────────────────────────────────────────────────────────┐
│                      ERROR SCENARIOS                                         │
└─────────────────────────────────────────────────────────────────────────────┘

Scenario 1: Evaluation Fails
────────────────────────────
Background Thread:
├─ Groq API returns error
├─ Set status='error'
├─ Set eval_error='API rate limit exceeded'
└─ Commit to DB

Candidate:
├─ Poll returns status='error'
├─ Show "Evaluation failed" badge
├─ Display error message
└─ Stop polling

Scenario 2: Recruiter Action Fails
───────────────────────────────────
Recruiter clicks Shortlist:
├─ POST /recruiter/action
├─ Backend returns 403 (Forbidden)
│  └─ Recruiter doesn't own the job
├─ Frontend shows Toast: "Forbidden"
└─ Button returns to normal state

Scenario 3: Candidate Withdraws
────────────────────────────────
Candidate clicks Withdraw:
├─ DELETE /candidate/evaluations/{eval_id}
├─ Backend deletes evaluation
├─ Frontend removes from list
└─ Polling stops


┌─────────────────────────────────────────────────────────────────────────────┐
│                      POLLING INTERVALS                                       │
└─────────────────────────────────────────────────────────────────────────────┘

Candidate Side:
┌─────────────────────────────────────────────────────────────────────────┐
│ Evaluation Polling (2 seconds)                                          │
│ ├─ Active: While eval_status = 'pending' or 'running'                   │
│ ├─ Stops: When eval_status = 'done' or 'error'                          │
│ └─ Endpoint: GET /candidate/evaluations/{eval_id}                       │
│                                                                         │
│ Action Polling (5 seconds)                                              │
│ ├─ Active: Always (while on Applications page)                          │
│ ├─ Checks: recruiter_action field                                       │
│ └─ Endpoint: GET /candidate/evaluations                                 │
└─────────────────────────────────────────────────────────────────────────┘

Recruiter Side:
┌─────────────────────────────────────────────────────────────────────────┐
│ Manual Refresh                                                          │
│ ├─ Click refresh button                                                 │
│ ├─ Endpoint: GET /candidates                                            │
│ └─ Updates candidates list                                              │
│                                                                         │
│ Auto-refresh on Action                                                  │
│ ├─ After shortlist/reject                                               │
│ ├─ Endpoint: GET /candidates                                            │
│ └─ Updates candidates list                                              │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                      NOTIFICATION FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

When Recruiter Shortlists:
┌──────────────────────────────────────────────────────────────────────┐
│ Backend:                                                             │
│ ├─ Create Notification                                              │
│ │  ├─ user_id = candidate.user_id                                   │
│ │  ├─ type = 'shortlisted'                                          │
│ │  ├─ title = "You've been shortlisted for Senior Backend Engineer!"│
│ │  ├─ body = "A recruiter shortlisted you for: Senior Backend..."   │
│ │  └─ link = "/candidate/applications"                              │
│ │                                                                    │
│ ├─ Send Email (if configured)                                       │
│ │  ├─ To: candidate@example.com                                     │
│ │  ├─ Subject: "You've been shortlisted!"                           │
│ │  └─ Body: HTML email with details                                 │
│ │                                                                    │
│ └─ Commit to DB                                                      │
│                                                                      │
│ Candidate:                                                           │
│ ├─ Sees notification in UI                                          │
│ ├─ Receives email (if configured)                                   │
│ └─ Sees updated badge on Applications page                          │
└──────────────────────────────────────────────────────────────────────┘

When Recruiter Rejects:
┌──────────────────────────────────────────────────────────────────────┐
│ Backend:                                                             │
│ ├─ Create Notification                                              │
│ │  ├─ user_id = candidate.user_id                                   │
│ │  ├─ type = 'status_changed'                                       │
│ │  ├─ title = "Application update: Senior Backend Engineer"         │
│ │  ├─ body = "Your evaluation for Senior Backend... was not selected"│
│ │  └─ link = "/candidate/applications"                              │
│ │                                                                    │
│ └─ Commit to DB                                                      │
│                                                                      │
│ Candidate:                                                           │
│ ├─ Sees notification in UI                                          │
│ └─ Sees updated badge on Applications page                          │
└──────────────────────────────────────────────────────────────────────┘
