from __future__ import annotations

import json
import os
import re

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are a technical hiring analyst. You analyze developer evidence and return structured "
    "skill assessments. Always respond with valid JSON only. No markdown, no explanation."
)


def extract_skills(
    github_data: dict,
    leetcode_data: dict,
    portfolio_text: str,
    trust_score: int,
) -> dict:
    """Call the Groq LLM to extract structured skills from collected evidence.

    Builds a rich prompt from GitHub, LeetCode, and portfolio signals.
    Returns parsed JSON dict with 'skills', 'hardest_function_summary', and
    'raw_summary'. On parse failure returns a safe empty structure with
    'llm_error' key set.
    """
    if not GROQ_API_KEY:
        return _empty_result("GROQ_API_KEY not set")

    repos = github_data.get("repos", [])

    # aggregate language list
    all_languages: dict = {}
    for repo in repos:
        for lang, bytes_count in repo.get("languages", {}).items():
            all_languages[lang] = all_languages.get(lang, 0) + bytes_count
    top_languages = sorted(all_languages, key=lambda l: all_languages[l], reverse=True)[:10]

    # collect sample commit messages
    all_messages: list[str] = []
    for repo in repos:
        all_messages.extend(repo.get("commit_messages", []))
    sample_messages = all_messages[:15]

    # collect code samples (truncated)
    code_parts: list[str] = []
    for repo in repos[:5]:
        for sample in repo.get("code_samples", [])[:2]:
            code_parts.append(f"--- {repo['name']} ---\n{sample[:800]}")
    code_block = "\n\n".join(code_parts) or "No code samples available."

    # leetcode summary line
    if leetcode_data and not leetcode_data.get("not_found") and not leetcode_data.get("error"):
        lc_line = (
            f"{leetcode_data.get('easy_solved', 0)} easy, "
            f"{leetcode_data.get('medium_solved', 0)} medium, "
            f"{leetcode_data.get('hard_solved', 0)} hard problems solved. "
            f"Global ranking: {leetcode_data.get('ranking', 'N/A')}"
        )
    else:
        lc_line = "No LeetCode data available."

    user_prompt = f"""Analyze this developer's profile and extract their skills.

GitHub summary:
- Total repos analyzed: {github_data.get('total_repos', 0)}
- Languages used (by bytes): {', '.join(top_languages) or 'unknown'}
- Sample commit messages: {json.dumps(sample_messages)}
- Code samples:
{code_block}

LeetCode: {lc_line}

Portfolio/Resume text: {portfolio_text[:1000] if portfolio_text else 'Not provided.'}

Trust score: {trust_score}/100 (lower = more integrity concerns — reduce confidence scores proportionally if below 60)

Return a JSON object with this exact structure:
{{
  "skills": [
    {{
      "name": "skill name",
      "confidence": 0.85,
      "depth": "working",
      "evidence": ["evidence string 1", "evidence string 2"],
      "recency_days": 30
    }}
  ],
  "hardest_function_summary": "one sentence describing the most complex code found",
  "raw_summary": "one paragraph about this developer's overall profile"
}}

depth must be one of: exposure, working, production
confidence is 0.0 to 1.0"""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        raw_content = response.choices[0].message.content
        clean = _strip_markdown(raw_content)
        return json.loads(clean)
    except json.JSONDecodeError:
        return _empty_result(f"LLM returned non-JSON response: {raw_content[:200]}")
    except Exception as e:
        return _empty_result(str(e))


def _strip_markdown(text: str) -> str:
    """Remove markdown code fences that some models wrap around JSON output."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


def _empty_result(error_msg: str) -> dict:
    """Safe fallback when LLM call or parsing fails."""
    return {
        "skills": [],
        "hardest_function_summary": "",
        "raw_summary": "",
        "llm_error": error_msg,
    }