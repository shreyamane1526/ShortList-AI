"""
Feedback Agent – Consolidates evaluation outputs into human-readable reports.

Generates:
  1. Candidate Report: Strengths, gaps, growth recommendations (markdown)
  2. Recruiter Summary: Match overview, interview questions, fairness assessment (markdown)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def generate_feedback_report(
    candidate: Any,
    job: Any,
    evaluation_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate comprehensive feedback reports for both candidate and recruiter.
    
    Args:
        candidate: Candidate model instance
        job: Job model instance
        evaluation_result: Dict with keys: score, recommendation, strengths, gaps, why_fit
    
    Returns:
        Dict with keys: candidate_report, recruiter_summary, interview_questions, fairness_assessment
    """
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        raise ValueError(
            "GROQ_API_KEY is required for feedback generation. "
            "Set it in Backend/.env to enable AI-powered reports."
        )
    
    try:
        from groq import Groq  # type: ignore
        client = Groq(api_key=groq_key)
        
        # Prepare candidate context
        candidate_skills = list({*(candidate.skills or []), *(candidate.resume_skills or [])})
        github_summary = ""
        if candidate.github_repos:
            github_summary = (
                f"- **GitHub**: {candidate.github_repos} repos, {candidate.github_stars or 0} stars, "
                f"top languages: {', '.join(candidate.github_top_languages or [])}\n"
            )
        lc_summary = ""
        if candidate.lc_easy is not None:
            lc_summary = (
                f"- **LeetCode**: {candidate.lc_easy} easy, {candidate.lc_medium or 0} medium, "
                f"{candidate.lc_hard or 0} hard problems solved\n"
            )
        
        # Extract evaluation data
        score = evaluation_result.get("score", 0)
        recommendation = evaluation_result.get("recommendation", "NO")
        strengths = evaluation_result.get("strengths", [])
        gaps = evaluation_result.get("gaps", [])
        why_fit = evaluation_result.get("why_fit", "")
        
        # ─────────────────────────────────────────────────────────────────────
        # 1. Generate Candidate Report
        # ─────────────────────────────────────────────────────────────────────
        candidate_prompt = f"""You are a career coach helping a candidate understand their job match evaluation.

JOB: {job.title} at {job.company}
MATCH SCORE: {score}/100
RECOMMENDATION: {"Strong Match" if recommendation == "YES" else "Partial Match"}

EVALUATION SUMMARY:
{why_fit}

STRENGTHS:
{chr(10).join(f"- {s}" for s in strengths)}

GAPS:
{chr(10).join(f"- {g}" for g in gaps)}

CANDIDATE PROFILE:
- Skills: {', '.join(candidate_skills[:20])}
{github_summary}{lc_summary}

Generate a **candidate-facing report** in markdown format with these sections:

## 📊 Your Match Score
[Explain the {score}/100 score in encouraging terms]

## 💪 Your Strengths
[List 3-5 key strengths that align with this role, with brief explanations]

## 🎯 Areas for Growth
[List 2-4 skill gaps or areas to develop, framed constructively]

## 🚀 Next Steps
[3-4 actionable recommendations for improving their candidacy or preparing for interviews]

## 📚 Learning Resources
[Suggest 2-3 specific resources (courses, books, projects) to address gaps]

Keep it encouraging, actionable, and under 500 words. Use markdown formatting."""

        candidate_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": candidate_prompt}],
            temperature=0.7,
            max_tokens=1024,
        )
        candidate_report = candidate_response.choices[0].message.content.strip()
        
        # ─────────────────────────────────────────────────────────────────────
        # 2. Generate Recruiter Summary
        # ─────────────────────────────────────────────────────────────────────
        recruiter_prompt = f"""You are an expert technical recruiter reviewing a candidate evaluation.

JOB: {job.title} at {job.company}
REQUIRED SKILLS: {', '.join(job.skills_required or [])}
JOB DESCRIPTION: {(job.description or '')[:800]}

CANDIDATE: {candidate.user.full_name if candidate.user else 'Unknown'}
MATCH SCORE: {score}/100
RECOMMENDATION: {recommendation}

EVALUATION:
{why_fit}

STRENGTHS:
{chr(10).join(f"- {s}" for s in strengths)}

GAPS:
{chr(10).join(f"- {g}" for g in gaps)}

CANDIDATE BACKGROUND:
- Headline: {candidate.headline or 'N/A'}
- Experience: {candidate.years_experience or 'Unknown'} years
- Skills: {', '.join(candidate_skills[:25])}
{github_summary}{lc_summary}

Generate a **recruiter-facing summary** in markdown format with these sections:

## 🎯 Match Overview
[2-3 sentence executive summary of the candidate's fit]

## ✅ Key Strengths
[3-5 bullet points highlighting why this candidate is a good fit]

## ⚠️ Considerations
[2-4 bullet points on gaps or areas to probe in interviews]

## 💡 Hiring Recommendation
[Clear recommendation: "Strongly Recommend", "Recommend with Reservations", or "Not Recommended" with 1-2 sentence rationale]

Keep it professional, data-driven, and under 400 words."""

        recruiter_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": recruiter_prompt}],
            temperature=0.5,
            max_tokens=1024,
        )
        recruiter_summary = recruiter_response.choices[0].message.content.strip()
        
        # ─────────────────────────────────────────────────────────────────────
        # 3. Generate Interview Questions
        # ─────────────────────────────────────────────────────────────────────
        questions_prompt = f"""You are a technical interviewer preparing questions for a candidate.

JOB: {job.title}
REQUIRED SKILLS: {', '.join(job.skills_required or [])}

CANDIDATE STRENGTHS:
{chr(10).join(f"- {s}" for s in strengths)}

CANDIDATE GAPS:
{chr(10).join(f"- {g}" for g in gaps)}

Generate 5-7 targeted interview questions as a JSON array. Include:
- 2-3 questions to validate their strengths
- 2-3 questions to probe their gaps
- 1-2 behavioral questions

Format: ["Question 1?", "Question 2?", ...]

Return ONLY the JSON array, no markdown, no explanation."""

        questions_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": questions_prompt}],
            temperature=0.6,
            max_tokens=512,
        )
        questions_raw = questions_response.choices[0].message.content.strip()
        
        # Parse JSON array
        if questions_raw.startswith("```"):
            questions_raw = questions_raw.split("```")[1]
            if questions_raw.startswith("json"):
                questions_raw = questions_raw[4:]
        questions_raw = questions_raw.strip()
        
        try:
            interview_questions = json.loads(questions_raw)
            if not isinstance(interview_questions, list):
                interview_questions = []
        except json.JSONDecodeError:
            # Fallback: extract questions from text
            interview_questions = [
                line.strip().lstrip("0123456789.-) ").strip()
                for line in questions_raw.split("\n")
                if line.strip() and "?" in line
            ][:7]
        
        # ─────────────────────────────────────────────────────────────────────
        # 4. Generate Fairness Assessment
        # ─────────────────────────────────────────────────────────────────────
        fairness_prompt = f"""You are a DEI (Diversity, Equity, Inclusion) expert reviewing a hiring evaluation for bias.

JOB: {job.title}
CANDIDATE EVALUATION SUMMARY:
{why_fit}

STRENGTHS: {', '.join(strengths[:5])}
GAPS: {', '.join(gaps[:5])}

Analyze this evaluation for potential bias. Consider:
- Are the criteria objective and job-relevant?
- Are there any assumptions based on background rather than skills?
- Is the language inclusive and professional?
- Are gaps framed constructively?

Provide a brief fairness assessment (2-3 sentences) and a bias risk score:
- LOW: Evaluation is objective and fair
- MEDIUM: Minor concerns, recommend review
- HIGH: Significant bias detected, requires intervention

Format as markdown:
## Fairness Assessment
[2-3 sentence analysis]

**Bias Risk**: [LOW/MEDIUM/HIGH]"""

        fairness_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": fairness_prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        fairness_assessment = fairness_response.choices[0].message.content.strip()

        # ─────────────────────────────────────────────────────────────────────
        # 5. Generate Adaptive Learning Path
        # ─────────────────────────────────────────────────────────────────────
        learning_prompt = f"""You are a career development expert creating a personalized learning plan.

JOB: {job.title} at {job.company}
REQUIRED SKILLS: {', '.join(job.skills_required or [])}
JOB DESCRIPTION: {(job.description or '')[:500]}

CANDIDATE PROFILE:
- Current Skills: {', '.join(candidate_skills[:20])}
- Experience: {candidate.years_experience or 'Unknown'} years
{github_summary}{lc_summary}

SKILL GAPS IDENTIFIED:
{chr(10).join(f"- {g}" for g in gaps)}

STRENGTHS TO BUILD UPON:
{chr(10).join(f"- {s}" for s in strengths)}

Create an adaptive 4-week learning plan that addresses skill gaps and incorporates current job market trends. Include:

1. **Weekly Plan**: 4 weeks of focused learning with specific goals
2. **Resources**: Mix of YouTube videos, Coursera courses, GitHub repos, articles
3. **Task Checklist**: 8-12 actionable tasks with completion tracking
4. **Market Trends**: Current industry trends to consider

Format as JSON:
{{
  "weekly_plan": [
    {{
      "week": 1,
      "focus": "Core fundamentals",
      "goals": ["Goal 1", "Goal 2"],
      "estimated_hours": 10
    }},
    ...
  ],
  "resources": [
    {{
      "title": "Resource Title",
      "type": "youtube|course|repo|article",
      "url": "https://...",
      "description": "Brief description",
      "duration": "2h video" // optional
    }},
    ...
  ],
  "task_checklist": [
    {{
      "id": "task_1",
      "task": "Complete X tutorial",
      "completed": false,
      "week": 1,
      "resource_url": "https://...",
      "type": "learning|practice|project"
    }},
    ...
  ],
  "market_trends": [
    "Trend 1: Brief explanation",
    "Trend 2: Brief explanation"
  ]
}}

Return ONLY valid JSON, no markdown."""

        learning_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": learning_prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        learning_raw = learning_response.choices[0].message.content.strip()
        
        # Parse JSON
        if learning_raw.startswith("```"):
            learning_raw = learning_raw.split("```")[1]
            if learning_raw.startswith("json"):
                learning_raw = learning_raw[4:]
        learning_raw = learning_raw.strip()
        
        try:
            learning_data = json.loads(learning_raw)
            learning_resources = learning_data
            task_checklist = learning_data.get("task_checklist", [])
        except json.JSONDecodeError:
            logger.warning("Failed to parse learning plan JSON, using fallback")
            learning_resources = {"weekly_plan": [], "resources": [], "market_trends": []}
            task_checklist = []
        
        return {
            "candidate_report": candidate_report,
            "recruiter_summary": recruiter_summary,
            "interview_questions": interview_questions,
            "fairness_assessment": fairness_assessment,
            "learning_resources": learning_resources,
            "task_checklist": task_checklist,
        }
        
    except Exception as exc:
        logger.error("Feedback generation failed: %s", exc)
        # Return minimal fallback reports
        return {
            "candidate_report": _generate_fallback_candidate_report(candidate, job, evaluation_result),
            "recruiter_summary": _generate_fallback_recruiter_summary(candidate, job, evaluation_result),
            "interview_questions": _generate_fallback_questions(job, evaluation_result),
            "fairness_assessment": "## Fairness Assessment\nAutomatic assessment unavailable. Manual review recommended.\n\n**Bias Risk**: MEDIUM",
            "learning_resources": {"weekly_plan": [], "resources": [], "market_trends": []},
            "task_checklist": [],
        }


def _generate_fallback_candidate_report(candidate: Any, job: Any, result: dict) -> str:
    """Fallback candidate report when Groq API fails."""
    score = result.get("score", 0)
    strengths = result.get("strengths", [])
    gaps = result.get("gaps", [])
    
    report = f"""# Your Match Report: {job.title}

## 📊 Your Match Score
You scored **{score}/100** for this role. {"This is a strong match!" if score >= 70 else "There's potential here with some skill development."}

## 💪 Your Strengths
"""
    for s in strengths[:5]:
        report += f"- {s}\n"
    
    report += "\n## 🎯 Areas for Growth\n"
    for g in gaps[:4]:
        report += f"- {g}\n"
    
    report += """
## 🚀 Next Steps
1. Review the job requirements and identify which skills to prioritize
2. Build projects that demonstrate the required skills
3. Prepare examples from your experience that showcase your strengths
4. Consider online courses or certifications for skill gaps

Good luck with your application!
"""
    return report


def _generate_fallback_recruiter_summary(candidate: Any, job: Any, result: dict) -> str:
    """Fallback recruiter summary when Groq API fails."""
    score = result.get("score", 0)
    recommendation = result.get("recommendation", "NO")
    strengths = result.get("strengths", [])
    gaps = result.get("gaps", [])
    why_fit = result.get("why_fit", "")
    
    summary = f"""# Candidate Evaluation: {candidate.user.full_name if candidate.user else 'Unknown'}

## 🎯 Match Overview
Match Score: **{score}/100** | Recommendation: **{recommendation}**

{why_fit}

## ✅ Key Strengths
"""
    for s in strengths[:5]:
        summary += f"- {s}\n"
    
    summary += "\n## ⚠️ Considerations\n"
    for g in gaps[:4]:
        summary += f"- {g}\n"
    
    summary += f"""
## 💡 Hiring Recommendation
{"**Strongly Recommend**: This candidate shows strong alignment with the role requirements." if score >= 80 else "**Recommend with Reservations**: Candidate has potential but requires skill development in key areas." if score >= 60 else "**Not Recommended**: Significant skill gaps present."}
"""
    return summary


def _generate_fallback_questions(job: Any, result: dict) -> list[str]:
    """Fallback interview questions when Groq API fails."""
    strengths = result.get("strengths", [])
    gaps = result.get("gaps", [])
    
    questions = [
        f"Can you walk me through your experience with {job.title.lower()} roles?",
        "What's your approach to learning new technologies?",
        "Describe a challenging project you've worked on recently.",
    ]
    
    if strengths:
        questions.append(f"Tell me about your experience with {strengths[0].lower()}.")
    
    if gaps:
        gap_skill = gaps[0].replace("Missing: ", "").replace("missing ", "")
        questions.append(f"How would you approach learning {gap_skill}?")
    
    questions.extend([
        "How do you handle tight deadlines and competing priorities?",
        "What questions do you have about this role or our team?",
    ])
    
    return questions[:7]
