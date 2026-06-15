"""
Deterministic learning resource retrieval.
"""

from __future__ import annotations


RESOURCE_DB = {

    "python": {
        "topics": [
            "Functions",
            "OOP",
            "Async programming",
            "Error handling",
        ],
        "projects": [
            "CLI Task Manager",
            "REST API"
        ],
        "estimated_time": "2-3 weeks",
    },

    "fastapi": {
        "topics": [
            "Routing",
            "Pydantic",
            "Dependency Injection",
            "JWT Authentication",
        ],
        "projects": [
            "Blog API",
            "Auth Service"
        ],
        "estimated_time": "1-2 weeks",
    },

    "postgresql": {
        "topics": [
            "SQL",
            "Indexes",
            "Joins",
            "Schema Design",
        ],
        "projects": [
            "E-commerce Database"
        ],
        "estimated_time": "1-2 weeks",
    },

    "docker": {
        "topics": [
            "Containers",
            "Dockerfiles",
            "Docker Compose",
        ],
        "projects": [
            "Containerize FastAPI App"
        ],
        "estimated_time": "1 week",
    },

    "redis": {
        "topics": [
            "Caching",
            "Pub/Sub",
            "Sessions",
        ],
        "projects": [
            "Redis Cache Layer"
        ],
        "estimated_time": "4-5 days",
    },

    "system design": {
        "topics": [
            "Scalability",
            "Caching",
            "Queues",
            "Load Balancing",
        ],
        "projects": [
            "Design Twitter Backend"
        ],
        "estimated_time": "3-4 weeks",
    },
}


def retrieve_learning_resources(
    skill_gaps: list,
) -> list[dict]:

    resources = []

    for gap in skill_gaps:

        skill = str(
            gap.get(
                "skill_name",
                "",
            )
        ).lower()

        if skill in RESOURCE_DB:

            data = RESOURCE_DB[skill]

            resources.append({

                "skill": skill,

                "priority": gap.get(
                    "severity",
                    "moderate",
                ),

                "topics": data[
                    "topics"
                ],

                "projects": data[
                    "projects"
                ],

                "estimated_time": data[
                    "estimated_time"
                ],
            })

    return resources