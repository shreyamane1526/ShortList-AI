"""
LLM roadmap generator.
"""

from __future__ import annotations

import json

from groq import Groq

from core.config import settings


client = Groq(
    api_key=settings.GROQ_API_KEY
)


def generate_learning_roadmap(
    skill_gaps: list,
    learning_resources: list,
    accessibility_mode: str = "standard",
) -> dict:

    prompt = f"""
You are an AI career mentor.

A candidate was rejected because of missing skills.

Your task:
1. Explain the missing skills.
2. Create a practical roadmap.
3. Prioritize critical gaps first.
4. Recommend realistic projects.
5. Keep the tone supportive and professional.
6. Avoid generic motivational advice.

Accessibility mode:
{accessibility_mode}

Missing skills:
{json.dumps(skill_gaps, indent=2)}

Learning resources:
{json.dumps(learning_resources, indent=2)}

Return STRICT JSON:

{{
  "summary": "...",
  "estimated_total_time": "...",
  "phases": [
    {{
      "phase": "...",
      "focus": "...",
      "skills": [],
      "topics": [],
      "projects": []
    }}
  ]
}}
"""

    try:

        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate structured "
                        "career learning roadmaps."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        content = (
            response
            .choices[0]
            .message.content
        )

        print(
            "\n[roadmap_generator] RAW RESPONSE:\n"
        )

        print(content)

        import dirtyjson

        # Remove markdown wrappers if present

        content = content.strip()

        if content.startswith("```json"):

            content = (
                content
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        elif content.startswith("```"):

            content = (
                content
                .replace("```", "")
                .strip()
            )

        import dirtyjson

        parsed = dirtyjson.loads(
            content
        )

        return parsed

        return json.loads(content)

    except Exception as exc:

        print(
            f"[roadmap_generator] "
            f"LLM failed: {exc}"
        )

        return {
            "summary": (
                "Roadmap generation failed."
            ),
            "estimated_total_time": "Unknown",
            "phases": [],
        }