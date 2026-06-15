# Voice Bot Integration — Complete Summary

This document summarizes all changes made to integrate the LiveKit voice agent (Priya) with the existing platform.

## ✅ Bugs Fixed

### Bug 1 — graph.py: technical_score node routing
**Problem**: The graph had `technical_ask → END` which meant scoring never happened.

**Fix**: Changed to `technical_ask → technical_score`, and `technical_score` conditionally routes to `technical_ask` (next question), `END` (waiting for user input), or `close` (interview done).

**Files**: `real_voice_bot/graph.py`

---

### Bug 2 — agent.py: run_interview_step dispatcher phase mismatch
**Problem**: The dispatcher called `technical_score_node` when phase was `"technical_listen"`, but the node expected the user's answer to already be in state.

**Fix**: The dispatcher now correctly handles `"technical_listen"` by calling `technical_score_node` with the user's input, then checking if a follow-up was asked (phase stays `"technical_listen"`) or if we should continue to the next question.

**Files**: `real_voice_bot/agent.py`

---

### Bug 3 — utils.py: JSON file paths are relative
**Problem**: `load_questions_for_trade` opened files with bare filenames like `"Blue-collar-Trades.json"`, which broke when the process ran from any directory other than `real_voice_bot/nodes/`.

**Fix**: Use absolute paths by computing `_BOT_DIR = os.path.dirname(_NODES_DIR)` and joining with filenames.

**Files**: `real_voice_bot/nodes/utils.py`

---

### Bug 4 — technical.py: scores list accumulates duplicate entries on follow-up
**Problem**: When `needs_followup=True`, the node appended a score to `state["scores"]` AND set phase to `"technical_listen"`. On the NEXT call (the follow-up answer), it appended ANOTHER score for the same question.

**Fix**: Added `pending_score: Optional[int]` to `InterviewState`. When triggering a follow-up, the score is stored in `pending_score` (not committed to `scores`). When the question is finally resolved (good answer, weak answer, or skip), the best of `pending_score` and the new score is committed.

**Files**: `real_voice_bot/state.py`, `real_voice_bot/nodes/technical.py`

---

### Bug 5 — experience.py: candidate_turns count counts priming message
**Problem**: The priming message `"The candidate's name is..."` was injected as a "user" role message, which meant `candidate_turns` counted it as a real turn. This caused the experience phase to end after only 1 real exchange.

**Fix**: Changed the threshold from `>= 2` to `>= 3` to allow 3 real user turns.

**Files**: `real_voice_bot/nodes/experience.py`

---

### Bug 6 — agent.py: on_user_turn_completed blocks the event loop
**Problem**: `self.state = await loop.run_in_executor(None, lambda: run_interview_step(self.state))` captured `self.state` by reference. If two events fired close together, state could be corrupted.

**Fix**: Added `self._processing = asyncio.Lock()` and wrapped the executor call in `async with self._processing:`. Also captured state by value in the lambda: `lambda s=self.state: run_interview_step(s)`.

**Files**: `real_voice_bot/agent.py`

---

## ✅ Improvements

### Improvement 1 — Better language detection (icebreaker)
**Before**: `detect_language_preference` split on whitespace and did exact word match. It missed "I prefer hindi", "hindi please", "speak in kannada".

**After**: Uses regex `\b{language}\b` to match language name anywhere in the utterance.

**Files**: `real_voice_bot/agent.py`

---

### Improvement 2 — Graceful handling when Groq fails mid-interview
**Before**: If any LLM call raised (rate limit, network, etc.), the agent went silent.

**After**: Added `with_retry` decorator in `utils.py` that retries LLM calls up to 3 times with exponential backoff.

**Files**: `real_voice_bot/nodes/utils.py`

---

### Improvement 3 — Skip icebreaker when metadata already has trade + name
**Before**: The agent always asked for name, trade, and years of experience, even if the Backend already provided them in room metadata.

**After**: In `on_user_turn_completed`, after language selection, if `candidate_info` already has `name`, `trade`, and `years_of_experience`, skip directly to the experience phase.

**Files**: `real_voice_bot/agent.py`

---

### Improvement 4 — Publish live score to room after each technical question
**Before**: Scores were only visible at the end of the interview.

**After**: After `technical_score_node` commits a score, the agent publishes a data channel event on topic `"interview-scores"` with the current scores and average.

**Files**: `real_voice_bot/agent.py`

---

### Improvement 5 — Close interview gracefully if candidate disconnects
**Before**: If the candidate disconnected mid-interview, no results were saved.

**After**: In `on_exit`, if the interview has any scores or is past the icebreaker phase, save a partial result with `persist_interview_result(state, partial=True)`.

**Files**: `real_voice_bot/agent.py`

---

## ✅ Backend Integration

### New DB Model: `LiveKitInterview`
Tracks voice interview sessions. Fields:
- `candidate_id`, `evaluation_id`, `livekit_room`, `phone_number`, `trade`, `language`
- `scores` (JSON list of ints), `avg_score`, `fitment`, `weak_topics`, `feedback`, `transcript`
- `status` (started | completed | partial), `started_at`, `completed_at`

**Files**: `Backend/models.py`

---

### New API Routes

#### `POST /api/livekit/token`
Generates a LiveKit access token for the candidate. The token metadata includes all candidate info so the agent can pre-populate state.

**Request**:
```json
{
  "room_name": "interview-abc123",  // optional
  "candidate_name": "John Doe",
  "trade": "Electrician",
  "phone_number": "+91...",
  "email": "john@example.com",
  "job_id": 42,
  "user_id": 123
}
```

**Response**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "room_name": "interview-abc123",
  "ws_url": "wss://your-project.livekit.cloud"
}
```

---

#### `POST /api/livekit/webhook`
Receives LiveKit webhook events. On `room_finished` or `participant_left`, marks the `LiveKitInterview` record as completed.

**No auth required** (validated by `LIVEKIT_WEBHOOK_SECRET` if set).

---

#### `GET /api/candidate/livekit-interview/<eval_id>`
Returns the interview results for display in the frontend.

**Response**:
```json
{
  "id": 1,
  "livekit_room": "interview-abc123",
  "trade": "Electrician",
  "language": "Hindi",
  "scores": [8, 7, 9, 6, 8, 7, 9, 8, 7, 8],
  "avg_score": 7.7,
  "fitment": "Job-Ready",
  "weak_topics": ["Troubleshooting"],
  "feedback": {
    "strengths": ["Strong safety knowledge", "Good practical experience"],
    "improvements": ["Review troubleshooting procedures"]
  },
  "transcript": [...],
  "status": "completed",
  "started_at": "2026-05-23T10:00:00Z",
  "completed_at": "2026-05-23T10:15:00Z"
}
```

**Files**: `Backend/api.py`

---

### New Persistence Layer: `real_voice_bot/database.py`
Provides `save_result(...)` and `check_integrity_flag(...)` functions that persist interview results to the Backend PostgreSQL database.

**Files**: `real_voice_bot/database.py`

---

## ✅ Frontend Integration

### New Component: `LiveKitInterviewModal.tsx`
Replaces the old Web Speech API modal. Uses `@livekit/components-react` to:
1. Request a token from `/api/livekit/token`
2. Join the LiveKit room (audio only)
3. Display live transcript and scores via data channel
4. Show results screen when interview completes

**Files**: `frontend/src/components/interview/LiveKitInterviewModal.tsx`

---

### Updated: `Applications.tsx`
Replaced `VoiceInterviewModal` with `LiveKitInterviewModal`. The modal is triggered by clicking "Start AI Interview" on an evaluation.

**Files**: `frontend/src/pages/candidate/Applications.tsx`

---

### Deleted Old Web Speech API Files
The following files were removed because they used the browser Web Speech API instead of LiveKit:
- `frontend/src/components/interview/VoiceInterviewModal.tsx`
- `frontend/src/components/interview/InterviewPhaseIntro.tsx`
- `frontend/src/components/interview/InterviewPhaseActive.tsx`
- `frontend/src/components/interview/InterviewPhaseResults.tsx`
- `frontend/src/components/interview/MicButton.tsx`
- `frontend/src/hooks/useSpeechRecognition.ts`
- `frontend/src/hooks/useTextToSpeech.ts`
- `frontend/src/hooks/useInterview.ts`

---

## ✅ Dependencies Installed

### Frontend
```bash
npm install @livekit/components-react livekit-client
```

### Backend
```bash
pip install livekit-api
```

### Voice Bot Worker
```bash
pip install livekit livekit-agents livekit-plugins-sarvam langchain-groq langgraph python-dotenv sqlalchemy psycopg2-binary
```

---

## ✅ Environment Variables

### Backend `.env`
```bash
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
LIVEKIT_WEBHOOK_SECRET=your_webhook_secret
```

### Voice Bot `.env`
```bash
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=postgresql://user:password@localhost:5432/shortlist_ai
```

---

## ✅ How to Run

### 1. Start the Backend
```bash
cd Backend
python run.py
```

### 2. Start the Voice Bot Worker
```bash
cd real_voice_bot
python agent.py dev
```

### 3. Start the Frontend
```bash
cd frontend
npm run dev
```

### 4. Run the Migration (First Time Only)
```bash
cd Backend
python migrate_livekit.py
```

---

## ✅ Testing the Full Flow

1. As a candidate, navigate to an evaluation detail page
2. Click "Start AI Interview with Priya"
3. Grant microphone permission in browser
4. Say a language (e.g. "English" or "Hindi")
5. Priya should respond and begin the icebreaker
6. The live transcript should appear in the modal in real-time
7. After the interview, the results screen should show scores + transcript
8. Check backend DB that `LiveKitInterview` record was created

---

## ✅ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React + LiveKit React SDK)                           │
│  - Requests token from Backend /api/livekit/token               │
│  - Joins LiveKit room with audio only                           │
│  - Displays live transcript + scores via data channel           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Backend (Flask)                                                 │
│  - Generates LiveKit access token with candidate metadata       │
│  - Creates LiveKitInterview DB record                           │
│  - Receives webhook on room_finished                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LiveKit Cloud / Self-Hosted Server                             │
│  - Routes audio between candidate and agent                     │
│  - Publishes data channel events (transcript, scores)           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  real_voice_bot/agent.py (LiveKit Worker)                       │
│  - Runs as a persistent worker process                          │
│  - Connects to LiveKit room when candidate joins                │
│  - Orchestrates interview via LangGraph state machine           │
│  - Publishes transcript + scores to data channel                │
│  - Saves results to Backend DB via database.py                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ Key Constraints Followed

✓ Did NOT change the persona name (Priya) or tone in any node  
✓ Did NOT change Sarvam STT/TTS configuration  
✓ Did NOT add Web Speech API anywhere  
✓ Did NOT modify the JSON question files structure  
✓ All node files use relative imports: `from nodes.utils import ...`  
✓ The `real_voice_bot/database.py` `save_result` function is the source of truth for persistence  

---

## 🎉 Summary

All 6 bugs have been fixed, all 5 improvements have been implemented, the backend integration is complete, the frontend integration is complete, and all old Web Speech API files have been removed. The voice bot is now fully integrated with the platform and ready for testing!
