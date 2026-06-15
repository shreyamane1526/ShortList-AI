def extract_context(
    job_description: str,
):

    return {
        "role": "Backend Engineer",
        "required_skills": [
            {
                "name": "Python",
                "importance": 0.95,
            },
            {
                "name": "FastAPI",
                "importance": 0.88,
            },
        ],
        "preferred_skills": [
            {
                "name": "Docker",
                "importance": 0.65,
            }
        ],
    }