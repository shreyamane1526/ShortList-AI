"""
agents/reasoning_agent/nd_task_generator.py  — NEW FILE

PURPOSE:
  Generates role-appropriate, level-appropriate work sample tasks that
  adapt their FORMAT (not difficulty) based on ND profile.

CORE PRINCIPLE:
  The TASK itself is identical — every candidate is evaluated on the same skill.
  Only the PRESENTATION changes: chunked vs monolithic, code-first vs doc-first,
  structured specs vs open brief.

  This eliminates format-based unfair disadvantage WITHOUT giving easier tasks.

TASK DURATION RULES (per your specification):
  Junior (0-2y):  30 minutes
  Mid   (2-5y):   45 minutes
  Senior (5+y):   60 minutes
  Adaptive:       system decides based on role complexity

ROLE CATEGORIES (from your "all tech roles" selection):
  backend, frontend, fullstack, ml_ai, devops, data, mobile, systems

FORMAT ADAPTATION PER ND TYPE:
  ADHD:
    - Tasks broken into numbered micro-steps (max 3 min each)
    - One question visible at a time (chunked delivery)
    - Progress indicator shown
    - No open-ended "design whatever you want" tasks

  DYSLEXIA:
    - Code-first: starter scaffold provided, minimal reading
    - Instructions in bullet points (not paragraphs)
    - Optional audio/TTS flag set to True
    - Diagrams/examples before text descriptions

  AUTISM:
    - Fully specified: exact input format, exact output format
    - Expected output examples provided
    - No ambiguous requirements ("make it clean" → banned)
    - Edge cases explicitly stated upfront

  STANDARD:
    - Normal task presentation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict


# ══════════════════════════════════════════════════════════════════════════════
# Output types
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TaskStep:
    """One step in a chunked task (used in ADHD format)."""
    step_number: int
    instruction: str
    estimated_minutes: int
    success_criteria: str


@dataclass
class WorkSampleTask:
    """
    A complete work sample task, format-adapted for the candidate's ND profile.
    The difficulty_level and required_skills are role/level determined.
    The format fields are ND-adapted.
    """
    task_id:            str
    title:              str
    role_category:      str
    level:              str              # "junior" | "mid" | "senior"
    duration_minutes:   int
    nd_format:          str              # "adhd" | "dyslexia" | "autism" | "standard"

    # Core task content
    problem_statement:  str
    required_skills:    List[str]
    evaluation_criteria: List[str]
    starter_code:       Optional[str]    # provided for dyslexia format

    # Structured delivery
    steps:              List[TaskStep]   # populated for ADHD format
    input_spec:         Optional[str]   # exact input format for autism format
    output_spec:        Optional[str]   # exact output format for autism format
    example_io:         List[Dict]      # examples for autism format

    # Accessibility flags
    tts_enabled:        bool = False    # True for dyslexia format
    progress_indicator: bool = False    # True for ADHD format
    minimal_reading:    bool = False    # True for dyslexia format


# ══════════════════════════════════════════════════════════════════════════════
# Task library — role × level × skill
# ══════════════════════════════════════════════════════════════════════════════

# Each entry: (role_category, level, skill_focus, title, core_problem)
TASK_LIBRARY = {
    ("backend", "junior"): {
        "title":    "Build a REST endpoint",
        "skill":    "Python + REST API",
        "problem":  "Implement a single POST /users endpoint. It receives JSON with name and email, validates both fields are present and email is valid format, stores in an in-memory dict, and returns the created user with a generated ID. Return 400 for validation failures.",
        "criteria": ["Correct HTTP status codes", "Input validation working", "Returns valid JSON", "Edge cases handled (empty fields, malformed email)"],
        "starter":  'from flask import Flask, request, jsonify\nimport uuid\n\napp = Flask(__name__)\nusers = {}\n\n@app.route("/users", methods=["POST"])\ndef create_user():\n    # TODO: implement\n    pass\n',
        "input_spec": 'POST /users\nContent-Type: application/json\n{"name": "string (required)", "email": "string (required, valid email format)"}',
        "output_spec": 'Success (201): {"id": "uuid-string", "name": "...", "email": "..."}\nValidation error (400): {"error": "field_name is required|invalid"}',
        "examples": [
            {"input": '{"name": "Alice", "email": "alice@example.com"}', "output": '{"id": "abc-123", "name": "Alice", "email": "alice@example.com"}', "status": 201},
            {"input": '{"name": "Bob"}', "output": '{"error": "email is required"}', "status": 400},
            {"input": '{"name": "Carol", "email": "not-an-email"}', "output": '{"error": "email is invalid"}', "status": 400},
        ],
    },
    ("backend", "mid"): {
        "title":    "Design and implement a rate limiter",
        "skill":    "Python + System Design + Algorithms",
        "problem":  "Implement a sliding window rate limiter class. It should allow N requests per T seconds per user_id. If the limit is exceeded return False, else True and record the request. Write tests for at least 3 edge cases.",
        "criteria": ["Correct sliding window logic", "Per-user isolation", "Tests cover edge cases", "Clean, readable implementation"],
        "starter":  'import time\nfrom collections import defaultdict, deque\n\nclass RateLimiter:\n    def __init__(self, max_requests: int, window_seconds: int):\n        self.max_requests = max_requests\n        self.window_seconds = window_seconds\n        self.requests = defaultdict(deque)  # user_id → deque of timestamps\n\n    def is_allowed(self, user_id: str) -> bool:\n        # TODO: implement sliding window\n        pass\n',
        "input_spec": "RateLimiter(max_requests=5, window_seconds=60)\nrateLimiter.is_allowed(user_id: str) → bool",
        "output_spec": "True if request allowed (and recorded), False if rate limit exceeded",
        "examples": [
            {"input": "5 calls in 60s for user_a", "output": "True, True, True, True, True"},
            {"input": "6th call for user_a within 60s", "output": "False"},
            {"input": "6th call for user_a after 61s", "output": "True (window slid)"},
        ],
    },
    ("backend", "senior"): {
        "title":    "Design a distributed job queue",
        "skill":    "System Design + Python + Concurrency",
        "problem":  "Design and implement a simplified distributed job queue. Jobs have a payload, priority (1-10), and status (pending/running/done/failed). Implement: enqueue(job), dequeue() picks highest priority, mark_done(job_id), mark_failed(job_id, reason), get_status(job_id). Include retry logic: failed jobs retry up to 3 times with exponential backoff. Write tests.",
        "criteria": ["Priority ordering correct", "Retry logic with backoff", "Thread-safe implementation", "Clear status transitions", "Tests cover failure scenarios"],
        "starter":  'import time\nimport threading\nimport heapq\nfrom dataclasses import dataclass, field\nfrom typing import Optional\nfrom enum import Enum\n\nclass JobStatus(Enum):\n    PENDING = "pending"\n    RUNNING = "running"\n    DONE = "done"\n    FAILED = "failed"\n\n@dataclass\nclass Job:\n    id: str\n    payload: dict\n    priority: int\n    status: JobStatus = JobStatus.PENDING\n    retries: int = 0\n    # add fields as needed\n\nclass JobQueue:\n    def __init__(self):\n        pass  # TODO: implement\n',
        "input_spec": "JobQueue API: enqueue(job: Job), dequeue() → Job|None, mark_done(job_id), mark_failed(job_id, reason), get_status(job_id) → JobStatus",
        "output_spec": "Thread-safe implementation. Failed jobs retry ≤ 3 times with delays: 1s, 2s, 4s",
        "examples": [
            {"input": "enqueue job with priority 5, then job with priority 9", "output": "dequeue returns priority 9 job first"},
            {"input": "mark_failed called 3 times for same job", "output": "status becomes FAILED after 3rd retry"},
        ],
    },
    ("ml_ai", "junior"): {
        "title":    "Evaluate a classification model",
        "skill":    "Python + scikit-learn + ML evaluation",
        "problem":  "Given predictions and ground truth labels, compute: accuracy, precision, recall, F1 (macro and per-class). Identify which class is performing worst. Return results as a structured dict. Do NOT use sklearn's classification_report — implement the metrics manually.",
        "criteria": ["Correct metric formulas", "Per-class breakdown", "Identifies worst class", "Clean structured output"],
        "starter":  'def evaluate_classifier(y_true: list, y_pred: list, class_names: list) -> dict:\n    """\n    Args:\n        y_true: ground truth labels (integers)\n        y_pred: predicted labels (integers)\n        class_names: human-readable names for each class index\n    Returns:\n        dict with overall and per-class metrics\n    """\n    # TODO: implement without sklearn.metrics\n    pass\n',
        "input_spec": "y_true=[0,1,2,0,1,2], y_pred=[0,1,0,0,2,2], class_names=['cat','dog','bird']",
        "output_spec": '{"overall": {"accuracy": 0.67, "f1_macro": 0.58}, "per_class": {"cat": {"precision": 1.0, "recall": 1.0, "f1": 1.0}, ...}, "worst_class": "dog"}',
        "examples": [],
    },
    ("ml_ai", "senior"): {
        "title":    "Debug a leaky ML pipeline",
        "skill":    "Python + ML engineering + data leakage detection",
        "problem":  "The attached code trains a model and achieves 99% validation accuracy but only 52% on the test set. Identify all data leakage issues, explain why each is a problem, fix them, and verify the fixed model gives realistic performance. Document what you changed and why.",
        "criteria": ["All leakage sources identified", "Fixes are correct", "Explanation is clear", "Fixed model performance is realistic"],
        "starter":  'import numpy as np\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.linear_model import LogisticRegression\nfrom sklearn.model_selection import train_test_split\n\n# Deliberately broken code with data leakage\ndef train_leaky_model(X, y):\n    # BUG 1: scaling before split\n    scaler = StandardScaler()\n    X_scaled = scaler.fit_transform(X)\n    X_train, X_val, y_train, y_val = train_test_split(X_scaled, y, test_size=0.2)\n\n    # BUG 2: using test labels to select features\n    correlations = [abs(np.corrcoef(X_train[:, i], y_val[:len(X_train)])[0,1]) for i in range(X_train.shape[1])]\n    top_features = np.argsort(correlations)[-10:]\n\n    model = LogisticRegression()\n    model.fit(X_train[:, top_features], y_train)\n    val_acc = model.score(X_val[:, top_features], y_val)\n    print(f"Val accuracy: {val_acc:.2%}")  # prints ~99%\n    return model\n',
        "input_spec": "Fix the leaky pipeline above. Return corrected code + explanation dict.",
        "output_spec": '{"bugs_found": [...], "fixes_applied": [...], "fixed_val_accuracy": "realistic ~70-80%"}',
        "examples": [],
    },
    ("frontend", "mid"): {
        "title":    "Build an accessible component",
        "skill":    "JavaScript/TypeScript + Accessibility + CSS",
        "problem":  "Build a modal dialog component that: opens on button click, traps focus inside when open, closes on Escape key, closes when clicking outside, has correct ARIA attributes (role, aria-modal, aria-labelledby), and is keyboard navigable. No framework — vanilla JS only.",
        "criteria": ["Focus trap working", "Keyboard navigation correct", "ARIA attributes correct", "Click-outside closes", "Escape closes"],
        "starter":  '<!-- starter HTML -->\n<button id="open-btn">Open Modal</button>\n<div id="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" style="display:none">\n  <h2 id="modal-title">Modal Title</h2>\n  <p>Modal content here</p>\n  <button id="close-btn">Close</button>\n</div>\n\n<script>\n// TODO: implement modal logic\nconst openBtn = document.getElementById("open-btn");\nconst modal = document.getElementById("modal");\nconst closeBtn = document.getElementById("close-btn");\n</script>\n',
        "input_spec": "Vanilla JS modal. No external libraries.",
        "output_spec": "Working HTML+JS file. All 5 evaluation criteria pass.",
        "examples": [],
    },
    ("devops", "mid"): {
        "title":    "Write a deployment health checker",
        "skill":    "Python + HTTP + monitoring concepts",
        "problem":  "Write a health checker that: polls a list of endpoints every N seconds, tracks response time and status code per endpoint, detects when an endpoint is 'unhealthy' (status != 200 or response > 2s for 3 consecutive checks), sends an alert dict when unhealthy, and recovers when healthy again. Implement without external monitoring libraries.",
        "criteria": ["Polling interval correct", "3-consecutive-failure threshold", "Recovery detection", "Alert dict structure correct", "Clean async or threaded implementation"],
        "starter":  'import time\nimport requests\nfrom dataclasses import dataclass\nfrom typing import List, Callable, Dict\n\n@dataclass\nclass Endpoint:\n    url: str\n    name: str\n\ndef run_health_checker(\n    endpoints: List[Endpoint],\n    interval_seconds: int,\n    alert_callback: Callable[[Dict], None],\n) -> None:\n    # TODO: implement\n    pass\n',
        "input_spec": "endpoints=[Endpoint(url='http://...', name='api')], interval=30, alert_callback=fn",
        "output_spec": 'alert_callback receives: {"endpoint": "api", "url": "...", "status": "unhealthy", "consecutive_failures": 3, "last_response_time_ms": 3200}',
        "examples": [],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# Format adapters — transform core task into ND-specific presentation
# ══════════════════════════════════════════════════════════════════════════════

def _apply_adhd_format(task: WorkSampleTask, core: dict) -> WorkSampleTask:
    """
    Breaks the task into numbered micro-steps.
    Each step is self-contained and estimated at 3-8 minutes.
    Progress indicator enabled.
    """
    criteria = core["criteria"]
    steps = []
    for i, criterion in enumerate(criteria, 1):
        step_mins = max(3, task.duration_minutes // max(len(criteria), 1))
        steps.append(TaskStep(
            step_number       = i,
            instruction       = f"Focus only on: {criterion}. Complete this before moving on.",
            estimated_minutes = step_mins,
            success_criteria  = criterion,
        ))

    # Add a final integration step
    steps.append(TaskStep(
        step_number       = len(steps) + 1,
        instruction       = "Run your solution against the provided examples. Fix any failures.",
        estimated_minutes = max(5, task.duration_minutes // 5),
        success_criteria  = "All provided examples pass",
    ))

    task.steps             = steps
    task.progress_indicator = True
    task.problem_statement = (
        f"[STEP-BY-STEP MODE — complete each step before reading the next]\n\n"
        f"TASK: {task.title}\n\n"
        f"You have {task.duration_minutes} minutes total. "
        f"This is broken into {len(steps)} focused steps below. "
        f"Start with Step 1 only.\n\n"
        + core["problem"]
    )
    return task


def _apply_dyslexia_format(task: WorkSampleTask, core: dict) -> WorkSampleTask:
    """
    Code-first: starter scaffold is prominent, minimal reading.
    Instructions are bullet points, not paragraphs.
    TTS flag enabled.
    Example inputs/outputs shown before description.
    """
    task.tts_enabled     = True
    task.minimal_reading = True

    # Restructure: examples first, then bullet requirements, then description last
    examples_text = ""
    if task.example_io:
        examples_text = "\nEXAMPLES (what your code must handle):\n"
        for ex in task.example_io:
            examples_text += f"  INPUT:  {ex.get('input', '')}\n"
            examples_text += f"  OUTPUT: {ex.get('output', '')}\n\n"

    bullet_criteria = "\n".join(f"  ✓ {c}" for c in core["criteria"])

    task.problem_statement = (
        f"TASK: {task.title}\n"
        f"TIME: {task.duration_minutes} minutes\n\n"
        f"YOUR REQUIREMENTS:\n{bullet_criteria}\n"
        f"{examples_text}"
        f"\nSTARTER CODE IS PROVIDED BELOW — read the code first, then the description.\n\n"
        f"DESCRIPTION (optional — the code above shows exactly what's needed):\n"
        + core["problem"]
    )
    return task


def _apply_autism_format(task: WorkSampleTask, core: dict) -> WorkSampleTask:
    """
    Fully specified: exact input/output format, all edge cases listed,
    no ambiguous language, examples for every case.
    """
    edge_cases = (
        "\nEDGE CASES YOU MUST HANDLE:\n"
        "  • Empty input (return appropriate error, not crash)\n"
        "  • Maximum valid input (must not exceed time/memory limits)\n"
        "  • Boundary values (first/last element, zero, negative if applicable)\n"
        "  • Invalid types (handle gracefully)\n"
    )

    task.problem_statement = (
        f"TASK: {task.title}\n"
        f"DURATION: {task.duration_minutes} minutes exactly\n\n"
        f"SPECIFICATION:\n{core['problem']}\n\n"
        f"INPUT FORMAT:\n{task.input_spec or 'See starter code'}\n\n"
        f"OUTPUT FORMAT:\n{task.output_spec or 'See examples below'}\n"
        f"{edge_cases}"
        f"\nEVALUATION CRITERIA (exactly these, in this order):\n"
        + "\n".join(f"  {i+1}. {c}" for i, c in enumerate(core["criteria"]))
        + "\n\nNOTE: Ambiguity is NOT intentional. If anything is unclear, add a comment with your assumption."
    )
    return task


# ══════════════════════════════════════════════════════════════════════════════
# Duration resolver
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_duration(level: str, role_category: str) -> int:
    """
    Per your spec: 30-60 min based on role.
    Junior: 30 min, Mid: 45 min, Senior: 60 min.
    """
    base = {"junior": 30, "mid": 45, "senior": 60}.get(level, 45)
    # Complex roles get the upper end of their range
    if role_category in ("systems", "ml_ai") and level != "junior":
        base = min(base + 10, 60)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# Level inference from evidence
# ══════════════════════════════════════════════════════════════════════════════

def _infer_level(evidence: dict) -> str:
    """
    Infer candidate level from GitHub signals when not explicitly set.
    """
    signals      = evidence.get("signals", {})
    total_repos  = signals.get("total_repos_analyzed", 0)
    complexity   = signals.get("project_complexity", "low")
    account_age  = signals.get("account_age_days", 0) or 0
    skills       = evidence.get("skills", [])
    prod_skills  = sum(1 for s in skills if s.get("depth") == "production")

    if account_age > 1825 and prod_skills >= 3 and complexity == "high":
        return "senior"
    elif account_age > 730 or prod_skills >= 2 or total_repos >= 8:
        return "mid"
    else:
        return "junior"


# ══════════════════════════════════════════════════════════════════════════════
# Role category resolver
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_role_category(job_title: str, domains_required: list) -> str:
    """Map JD job title to internal role category."""
    title = job_title.lower()
    if any(kw in title for kw in ["ml", "machine learning", "ai", "data scientist"]):
        return "ml_ai"
    if any(kw in title for kw in ["frontend", "front-end", "react", "vue", "angular"]):
        return "frontend"
    if any(kw in title for kw in ["devops", "sre", "platform", "infrastructure"]):
        return "devops"
    if any(kw in title for kw in ["fullstack", "full stack", "full-stack"]):
        return "frontend"   # use frontend task for fullstack
    if any(kw in title for kw in ["backend", "back-end", "api", "python", "java", "go"]):
        return "backend"
    # Fallback from domains
    if "data" in domains_required:
        return "ml_ai"
    if "devops" in domains_required:
        return "devops"
    return "backend"   # safe default


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════

def generate_task(
    evidence: dict,
    role_fit: dict,
    nd_format: str = "standard",
    level_override: str = None,
) -> WorkSampleTask:
    """
    Generates a work sample task adapted for the candidate.

    Args:
        evidence:       CandidateEvidence dict
        role_fit:       RoleFitModel dict
        nd_format:      "adhd" | "dyslexia" | "autism" | "standard"
        level_override: explicitly set level, else inferred from evidence
    """
    level         = level_override or _infer_level(evidence)
    job_title     = role_fit.get("job_title", "Software Engineer")
    domains_req   = role_fit.get("domains_required", [])
    role_category = _resolve_role_category(job_title, domains_req)
    duration      = _resolve_duration(level, role_category)

    # Look up task from library
    key  = (role_category, level)
    core = TASK_LIBRARY.get(key) or TASK_LIBRARY.get((role_category, "mid")) or TASK_LIBRARY[("backend", "mid")]

    task = WorkSampleTask(
        task_id           = f"{role_category}_{level}_{nd_format}",
        title             = core["title"],
        role_category     = role_category,
        level             = level,
        duration_minutes  = duration,
        nd_format         = nd_format,
        problem_statement = core["problem"],
        required_skills   = [core["skill"]],
        evaluation_criteria = core["criteria"],
        starter_code      = core.get("starter"),
        steps             = [],
        input_spec        = core.get("input_spec"),
        output_spec       = core.get("output_spec"),
        example_io        = core.get("examples", []),
        tts_enabled       = False,
        progress_indicator = False,
        minimal_reading   = False,
    )

    # Apply ND format adaptation
    if nd_format == "adhd":
        task = _apply_adhd_format(task, core)
    elif nd_format == "dyslexia":
        task = _apply_dyslexia_format(task, core)
    elif nd_format == "autism":
        task = _apply_autism_format(task, core)

    return task