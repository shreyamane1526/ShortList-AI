import os
import json
import random
import re
import functools
import time
import logging
from collections import defaultdict
from langchain_groq import ChatGroq

logger = logging.getLogger("skillfit.utils")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

# BUG 3 FIX: Use absolute paths so the agent works from any working directory
_NODES_DIR = os.path.dirname(os.path.abspath(__file__))
_BOT_DIR = os.path.dirname(_NODES_DIR)

JSON_FILES = [
    os.path.join(_BOT_DIR, "Blue-collar-Trades.json"),
    os.path.join(_BOT_DIR, "Polytechnic-Skilled-Roles.json"),
    os.path.join(_BOT_DIR, "Semi-Skilled-Workforce.json"),
]

# ── Software role detection ───────────────────────────────────────────────────

_SW_KEYWORDS = {
    "engineer", "developer", "programmer", "architect", "devops", "sre",
    "frontend", "backend", "fullstack", "full stack", "full-stack",
    "software", "web", "mobile", "android", "ios", "data scientist",
    "data engineer", "ml engineer", "machine learning", "ai engineer",
    "cloud engineer", "platform engineer", "site reliability",
    "react", "node", "python", "java", "golang", "rust", "typescript",
    "infrastructure", "security engineer", "qa engineer", "test engineer",
    "embedded", "firmware", "systems engineer",
}

def _is_software_trade(trade: str) -> bool:
    t = trade.lower()
    return any(kw in t for kw in _SW_KEYWORDS)


def _get_sw_domain(trade: str) -> str:
    t = trade.lower()
    if any(k in t for k in ("frontend", "front-end", "react", "vue", "angular", "ui engineer")):
        return "frontend"
    if any(k in t for k in ("backend", "back-end", "api", "django", "flask", "spring", "node", "express", "fastapi")):
        return "backend"
    if any(k in t for k in ("fullstack", "full stack", "full-stack")):
        return "fullstack"
    if any(k in t for k in ("devops", "sre", "site reliability", "kubernetes", "docker", "terraform", "cloud")):
        return "devops"
    if any(k in t for k in ("machine learning", "ml", "ai engineer", "data scientist", "nlp", "deep learning")):
        return "ml"
    if any(k in t for k in ("data engineer", "spark", "airflow", "etl", "pipeline")):
        return "data_engineering"
    if any(k in t for k in ("android", "ios", "mobile", "flutter", "react native", "swift", "kotlin")):
        return "mobile"
    return "software_general"


_DOMAIN_TOPICS = {
    "frontend": [
        "React & Component Architecture", "State Management", "Performance Optimization",
        "TypeScript", "CSS & Layout", "Accessibility", "SSR/CSR/ISR", "Testing",
    ],
    "backend": [
        "API Design", "Database Design & Optimization", "Authentication & Authorization",
        "Caching Strategies", "Concurrency & Async", "Microservices", "Scalability", "Security",
    ],
    "fullstack": [
        "React Architecture", "REST API Design", "Database Modeling",
        "Authentication Flows", "State Management", "Performance", "Deployment & CI/CD", "System Design",
    ],
    "devops": [
        "Container Orchestration", "CI/CD Pipeline Design", "Infrastructure as Code",
        "Observability & Monitoring", "Cloud Architecture", "Networking & Security", "Incident Response",
    ],
    "ml": [
        "Model Training & Evaluation", "Feature Engineering", "Overfitting & Regularization",
        "Transformer Architecture", "MLOps & Deployment", "Inference Optimization", "Data Pipelines",
    ],
    "data_engineering": [
        "ETL/ELT Pipeline Design", "Spark & Distributed Processing", "Data Warehouse Modeling",
        "Streaming (Kafka/Flink)", "SQL Optimization", "Orchestration", "Data Quality",
    ],
    "mobile": [
        "Activity/View Lifecycle", "State Management", "Memory Management",
        "Offline-first Architecture", "Performance Profiling", "Navigation Patterns", "Testing",
    ],
    "software_general": [
        "Data Structures & Algorithms", "System Design", "Object-Oriented Design",
        "Concurrency & Threading", "Database Fundamentals", "API Design",
        "Testing & TDD", "Code Quality", "Problem Solving", "Architecture Patterns",
    ],
}


def _generate_sw_questions_with_groq(
    trade: str,
    n: int = 10,
    job_description: str = "",
    candidate_skills: list | None = None,
    resume_summary: str = "",
    github_data: dict | None = None,
    experience_level: str = "mid",
    previous_answers: list | None = None,
    evaluation_scores: list | None = None,
) -> list:
    """
    Generate software engineering interview questions using Groq.
    Fully role-aware, JD-aware, resume-aware, and performance-adaptive.
    Returns a list of dicts with keys: topic, question, ideal_answer.
    """
    if not GROQ_API_KEY:
        logger.warning("[Utils] GROQ_API_KEY not set — cannot generate software questions")
        return []

    domain = _get_sw_domain(trade)
    topics = _DOMAIN_TOPICS.get(domain, _DOMAIN_TOPICS["software_general"])
    topics_str = "\n".join(f"- {t}" for t in topics[:8])

    candidate_skills = candidate_skills or []
    github_data = github_data or {}
    previous_answers = previous_answers or []
    evaluation_scores = evaluation_scores or []

    # ── Adaptive difficulty based on performance ──
    avg_score = round(sum(evaluation_scores) / len(evaluation_scores), 1) if evaluation_scores else None
    difficulty = "intermediate"
    if avg_score is not None:
        if avg_score >= 8.0:
            difficulty = "expert"
        elif avg_score >= 6.5:
            difficulty = "advanced"
        elif avg_score >= 4.5:
            difficulty = "intermediate"
        else:
            difficulty = "basic"

    # ── Skills string for prompt ──
    skills_str = ", ".join(candidate_skills[:12]) if candidate_skills else "not specified"

    # ── Resume summary ──
    resume_snippet = (resume_summary or "")[:500].strip()

    # ── GitHub highlights ──
    gh_languages = github_data.get("languages", [])
    gh_repos = github_data.get("top_repos", [])
    gh_lang_str = ", ".join(gh_languages[:6]) if gh_languages else ""
    gh_repo_str = "; ".join(gh_repos[:3]) if gh_repos else ""

    # ── Previous answer context for continuity ──
    prev_context = ""
    if previous_answers:
        prev_lines = []
        for i, pa in enumerate(previous_answers[-3:]):
            prev_q = pa.get("question", "")
            prev_a = pa.get("answer", "")
            prev_s = pa.get("score", "")
            if prev_q and prev_a:
                prev_lines.append(f"Q{i+1}: {prev_q}\nA: {prev_a} (score: {prev_s})")
        if prev_lines:
            prev_context = "PREVIOUS ANSWERS (maintain conversational continuity):\n" + "\n\n".join(prev_lines)

    # ── Build the prompt ──
    prompt = f"""You are a senior technical interviewer at a top-tier tech company (FAANG-level).
Generate {n} technical interview questions for a {trade} role.

STRICT DOMAIN RULES — you MUST follow these without exception:
- Generate questions ONLY about software engineering, computer science, and technology.
- NEVER generate questions about: HVAC, plumbing, electrical wiring, woodworking, construction,
  manufacturing, welding, carpentry, warehouse operations, safety compliance, mechanical trades,
  sheet metal, machining, fitter, turner, mason, painter, or ANY non-software topic.
- If you are unsure whether a topic is software-related, default to software engineering concepts.
- Zero tolerance for vocational, trade-school, or blue-collar topics.

ROLE-SPECIFIC FOCUS:
- Frontend Engineer: React, TypeScript, rendering, performance, accessibility, state management, SSR/CSR, bundling
- Backend Engineer: APIs, DB design, scaling, auth, concurrency, caching, microservices, message queues
- Full Stack: Mix frontend + backend intelligently with system design
- ML/AI Engineer: transformers, embeddings, vector DBs, training pipelines, evaluation metrics, inference optimization
- DevOps/SRE: CI/CD, k8s, infrastructure as code, observability, incident response
- Mobile: activity lifecycle, memory management, offline-first, platform APIs
- Data Engineer: ETL pipelines, streaming, warehouse modeling, orchestration

INTERVIEW CONTEXT:
- Role: {trade}
- Domain: {domain.replace('_', ' ').title()}
- Difficulty Level: {difficulty}
- Experience Level: {experience_level}

JOB DESCRIPTION CONTEXT:
{job_description[:600] if job_description else 'Not provided'}

CANDIDATE SKILLS: {skills_str}

RESUME PROJECTS & BACKGROUND:
{resume_snippet if resume_snippet else 'Not provided'}

GITHUB DATA:
{("Languages: " + gh_lang_str) if gh_lang_str else ''}
{("Notable repos: " + gh_repo_str) if gh_repo_str else ''}

{prev_context}

QUESTION QUALITY REQUIREMENTS:
- Sound like a real senior engineer asking, not a textbook or HR bot
- Reference the candidate's actual skills, projects, or resume experience where possible
- Avoid "What is X?" style questions — ask about application, trade-offs, and real scenarios
- Each question should feel like it belongs in a Google/Meta/Amazon interview
- BAD: "What is React?" GOOD: "You've worked with React — walk me through how you'd optimise a component that re-renders too frequently."
- BAD: "What is a database?" GOOD: "Given your PostgreSQL experience, how would you approach indexing a table with 50M rows?"
- For {difficulty} difficulty: {"ask about complex trade-offs, performance, and system design" if difficulty == "expert" else "ask about practical application and moderate depth" if difficulty == "advanced" else "cover fundamentals with practical application" if difficulty == "intermediate" else "focus on core concepts and foundational knowledge"}

FOCUS TOPICS FOR THIS ROLE:
{topics_str}

Return ONLY a JSON array of {n} objects:
[
  {{
    "topic": "<focus area label>",
    "question": "<the full interview question>",
    "ideal_answer": "<key points a strong answer should cover, 2-3 sentences>"
  }},
  ...
]

No markdown. No explanation. Just the JSON array."""

    try:
        llm = ChatGroq(
            model=GROQ_MODEL,
            groq_api_key=GROQ_API_KEY,
            max_tokens=3000,
            temperature=0.7,
        )
        result = llm.invoke(prompt)
        raw = result.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        questions = json.loads(raw)
        if not isinstance(questions, list):
            raise ValueError("Expected a JSON array")
        logger.info(f"[Utils] Generated {len(questions)} Groq questions for '{trade}' ({domain}) at {difficulty} difficulty")
        # Attach difficulty metadata to each question
        for q in questions:
            q["difficulty"] = difficulty
        return questions[:n]
    except Exception as e:
        logger.error(f"[Utils] Groq question generation failed for '{trade}': {e}")
        return []


def with_retry(max_attempts=3, delay=1.5):
    """IMPROVEMENT 2: Decorator to retry LLM calls on transient failures."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"[Retry {attempt + 1}] {fn.__name__} failed: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator

def get_llm(temperature=0.7, max_tokens=150):
    return ChatGroq(
        model=GROQ_MODEL,
        groq_api_key=GROQ_API_KEY,
        max_tokens=max_tokens,
        temperature=temperature,
    )

def build_messages(system_prompt: str, history: list) -> list:
    """Builds the message list for a Groq call — system + history."""
    return [{"role": "system", "content": system_prompt}] + history

def strip_tag(text: str, tag: str) -> str:
    """Removes a system tag from response text before speaking."""
    return text.replace(tag, "").strip()

def _normalise_trade_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

def load_questions_for_trade(
    trade: str,
    job_description: str = "",
    candidate_skills: list | None = None,
    resume_summary: str = "",
    github_data: dict | None = None,
    experience_level: str = "mid",
    previous_answers: list | None = None,
    evaluation_scores: list | None = None,
) -> list:
    """
    Load interview questions for a given trade/role.

    For software engineering roles: generates questions via Groq so they are
    always domain-appropriate (never HVAC/woodworking/construction) and fully
    role-aware, JD-aware, resume-aware, and performance-adaptive.

    For non-software trades: loads from the JSON files as before.
    Returns up to 10 questions as dicts with keys: topic, question, ideal_answer.
    """
    # ── Software roles: use Groq ─────────────────────────────────────────────
    if _is_software_trade(trade):
        questions = _generate_sw_questions_with_groq(
            trade,
            n=10,
            job_description=job_description,
            candidate_skills=candidate_skills,
            resume_summary=resume_summary,
            github_data=github_data,
            experience_level=experience_level,
            previous_answers=previous_answers,
            evaluation_scores=evaluation_scores,
        )
        if questions:
            return questions
        # Groq failed — return a safe software-generic fallback (never vocational)
        logger.warning(f"[Utils] Groq failed for '{trade}', using software fallback questions")
        domain = _get_sw_domain(trade)
        topics = _DOMAIN_TOPICS.get(domain, _DOMAIN_TOPICS["software_general"])
        return [
            {"topic": topics[i % len(topics)], "question": q, "ideal_answer": ""}
            for i, q in enumerate([
                f"Walk me through a challenging technical problem you solved as a {trade}.",
                "How do you approach system design for a new feature from scratch?",
                "Describe a time you had to make a significant architectural trade-off.",
                "How do you ensure code quality and reliability in your team?",
                "Tell me about a performance bottleneck you identified and fixed.",
                "How do you handle disagreements about technical decisions with teammates?",
                "What's your approach to testing — unit, integration, and end-to-end?",
                "Describe your experience with CI/CD and deployment pipelines.",
                "How do you stay current with new technologies and best practices?",
                "Tell me about a time you had to learn a new technology quickly for a project.",
            ])
        ]

    # ── Non-software trades: load from JSON files ────────────────────────────
    trade_data = None
    all_trade_data = []
    requested_trade = _normalise_trade_name(trade)

    for file in JSON_FILES:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
            all_trade_data.extend(data.values())

            normalised_keys = {
                key: _normalise_trade_name(key)
                for key in data
            }

            for key, normalised_key in normalised_keys.items():
                if normalised_key == requested_trade:
                    trade_data = data[key]
                    break
            if not trade_data and requested_trade:
                for key, normalised_key in normalised_keys.items():
                    if requested_trade in normalised_key or normalised_key in requested_trade:
                        trade_data = data[key]
                        break
        except FileNotFoundError:
            continue
        if trade_data:
            break

    if not trade_data:
        trade_data = {}
        for candidate_trade in all_trade_data:
            for topic, q_list in candidate_trade.items():
                trade_data.setdefault(topic, []).extend(q_list[:2])

    # Round-robin across topics for coverage
    topic_buckets = defaultdict(list)
    for topic, q_list in trade_data.items():
        for q in q_list:
            topic_buckets[topic].append({
                "topic": topic,
                "question": q["question"],
                "ideal_answer": q["ideal_answer"]
            })

    for topic in topic_buckets:
        random.shuffle(topic_buckets[topic])

    selected = []
    topic_keys = list(topic_buckets.keys())
    i = 0
    while len(selected) < 10 and any(topic_buckets[t] for t in topic_keys):
        topic = topic_keys[i % len(topic_keys)]
        if topic_buckets[topic]:
            selected.append(topic_buckets[topic].pop(0))
        i += 1

    random.shuffle(selected)
    return selected
