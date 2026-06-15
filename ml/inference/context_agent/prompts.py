SYSTEM_PROMPT = """
Extract structured hiring requirements from job descriptions.

Return ONLY valid JSON.

Required format:

{
  "role": "...",
  "required_skills": [
    {
      "name": "...",
      "importance": 0.95
    }
  ],
  "preferred_skills": []
}
"""