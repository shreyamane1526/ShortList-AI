import json

from agents.context_agent.schemas import JobContext

from agents.context_agent.normalizer import (
    normalize_skill,
)


def validate_dataset_entry(entry):

    try:

        output = entry["output"]

        required = output["required_skills"]

        preferred = output["preferred_skills"]

        seen = set()

        for skill in required + preferred:

            normalized = normalize_skill(
                skill["name"]
            )

            skill["name"] = normalized

            if normalized in seen:
                raise ValueError(
                    f"Duplicate skill: {normalized}"
                )

            seen.add(normalized)

        JobContext(**output)

        return True

    except Exception as e:
        print(f"Validation Error: {e}")
        return False