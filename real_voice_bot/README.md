# Real Voice Bot — Priya (AI SkillFit Interviewer)

A LiveKit-powered voice agent that conducts multilingual technical interviews for blue-collar and skilled trade candidates in India.

## What This Is

**Priya** is a warm, empathetic AI interviewer built with:
- **LiveKit Agents SDK** — server-side voice agent framework
- **Sarvam AI** — Indian multilingual STT/TTS (supports 12+ Indian languages)
- **Groq LLM** — llama-3.3-70b-versatile for reasoning and scoring
- **LangGraph** — state machine for interview flow (icebreaker → experience → technical → close)

## Architecture

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

## Interview Flow

1. **Language Selection** — Priya asks candidate to choose from 12 Indian languages
2. **Icebreaker** — Collects name, trade, years of experience
3. **Experience** — 2-3 conversational questions about work background
4. **Technical Round** — 10 trade-specific questions with follow-ups
5. **Close** — Warm closing with feedback summary

## Files

```
real_voice_bot/
├── agent.py                    # LiveKit entrypoint, VoiceAgent class
├── state.py                    # InterviewState TypedDict
├── graph.py                    # LangGraph state machine
├── database.py                 # Persistence to Backend PostgreSQL
├── nodes/
│   ├── icebreaker.py           # Language + name/trade extraction
│   ├── experience.py           # Work background conversation
│   ├── technical.py            # Question loading, scoring, closing
│   └── utils.py                # LLM helpers, question loader
├── Blue-collar-Trades.json     # Electrician, Plumber, Welder, etc.
├── Polytechnic-Skilled-Roles.json
├── Semi-Skilled-Workforce.json
└── .env.example                # Required environment variables
```

## Setup

### 1. Install Dependencies

```bash
cd real_voice_bot
pip install livekit livekit-agents livekit-plugins-sarvam langchain-groq langgraph python-dotenv sqlalchemy psycopg2-binary
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in:

```bash
# LiveKit (get from https://cloud.livekit.io/)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxx
LIVEKIT_API_SECRET=secretxxxxx

# Groq (get from https://console.groq.com/)
GROQ_API_KEY=gsk_xxxxx

# Database (same as Backend)
DATABASE_URL=postgresql://user:password@localhost:5432/shortlist_ai
```

### 3. Run the Agent Worker

```bash
python agent.py dev
```

This starts a LiveKit worker that listens for new rooms. When a candidate joins, the agent connects and begins the interview.

## Backend Integration

The Backend provides three routes:

### `POST /api/livekit/token`
Generates a LiveKit access token for the candidate. The token metadata includes:
- `name`, `trade`, `phone_number`, `email`, `job_id`, `user_id`, `livekit_room`

### `POST /api/livekit/webhook`
Receives LiveKit webhook events. On `room_finished`, marks the `LiveKitInterview` record as completed.

### `GET /api/candidate/livekit-interview/<eval_id>`
Returns the interview results (scores, transcript, fitment) for display in the frontend.

## Frontend Integration

The frontend uses `@livekit/components-react`:

```tsx
import LiveKitInterviewModal from '@/components/interview/LiveKitInterviewModal'

<LiveKitInterviewModal
  evalId={evalId}
  open={showInterview}
  onClose={() => setShowInterview(false)}
  candidateName={user?.full_name}
  trade={job.title}
  jobId={job.id}
/>
```

The modal:
1. Requests a token from `/api/livekit/token`
2. Joins the LiveKit room (audio only)
3. Displays live transcript and scores via data channel
4. Shows results screen when interview completes

## Data Channel Topics

The agent publishes two data channel topics:

### `interview-transcript`
```json
{
  "id": "assistant-1234567890",
  "speaker": "assistant" | "user",
  "text": "Hello! Welcome to AI SkillFit...",
  "timestamp": 1234567890
}
```

### `interview-scores`
```json
{
  "event": "score_update",
  "question_index": 3,
  "scores": [8, 7, 9, 6],
  "avg": 7.5
}
```

## Question Files

Questions are organized by trade category in JSON files:

```json
{
  "Electrician": {
    "Safety": [
      {
        "question": "What safety equipment do you use when working with live wires?",
        "ideal_answer": "Insulated gloves, safety goggles, voltage tester, rubber-soled shoes"
      }
    ],
    "Troubleshooting": [...]
  }
}
```

The agent loads 10 questions per interview, round-robin across topics for coverage.

## Scoring Logic

Each answer is scored 0-10 by `technical_score_node`:
- **8-10**: Excellent — covers key points, shows practical understanding
- **5-7**: Partial — understands basics but missing important aspects
- **3-4**: Weak — some awareness but significant gaps
- **0-2**: Very weak — incorrect or off-topic

Follow-up questions are triggered for scores 4-7 to give candidates a fair chance.

## Fitment Categories

Based on average score:
- **≥7.5**: Job-Ready
- **≥5.0**: Requires Training
- **≥3.0**: Low Confidence
- **<3.0**: Requires Significant Upskilling

Integrity flags (all scores identical, perfect 10 average, >50% zeros) trigger "Requires Manual Verification".

## Multilingual Support

Priya supports 12 Indian languages via Sarvam AI:
- English, Hindi, Bengali, Tamil, Telugu, Gujarati, Kannada, Malayalam, Marathi, Punjabi, Odia

The candidate selects their language at the start. All responses are translated to the chosen language before TTS.

## Development

### Run in Dev Mode
```bash
python agent.py dev
```

### Test with a Specific Room
```bash
python agent.py connect --room test-room-123 --url wss://your-project.livekit.cloud
```

### Logs
The agent logs all phase transitions, scores, and LLM calls to stdout. Use `logging.INFO` level for production.

## Troubleshooting

### Agent doesn't connect
- Check `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` in `.env`
- Ensure the LiveKit server is running and accessible
- Check firewall rules for WebSocket connections

### Questions not loading
- Verify JSON files are in the `real_voice_bot/` directory (not `nodes/`)
- Check `utils.py` uses absolute paths (`_BOT_DIR`)

### Scores not saving
- Check `DATABASE_URL` points to the same PostgreSQL database as Backend
- Ensure `livekit_interviews` table exists (created by `database.py`)
- Check Backend logs for save errors

### Follow-up questions loop infinitely
- This is fixed in Bug 4 — `pending_score` prevents duplicate score commits
- Ensure `state.py` includes `pending_score: Optional[int]`

## Production Deployment

1. **Run agent as a systemd service** (Linux) or supervisor process
2. **Set `LIVEKIT_WEBHOOK_SECRET`** and validate in Backend webhook handler
3. **Use PostgreSQL** (not SQLite) for concurrent writes
4. **Monitor agent logs** for LLM failures and retry exhaustion
5. **Set up LiveKit Cloud** or self-host with TURN servers for NAT traversal

## License

Part of the AI SkillFit platform — a government skill assessment program for Karnataka.
