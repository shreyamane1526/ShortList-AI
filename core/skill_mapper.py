from typing import List, Set

SKILL_EQUIVALENCE = {
    "backend": ["fastapi", "django", "flask", "spring", "node", "express"],
    "rest api": ["fastapi", "django", "flask", "express"],
    "database": ["postgresql", "mysql", "sqlite", "mongodb"],
    "devops": ["docker", "kubernetes", "ci/cd"],
}

def normalize_skills(skills: List[str]) -> Set[str]:
    normalized = set()

    for skill in skills:
        s = skill.lower()

        # direct
        normalized.add(s)

        # mapped
        for key, vals in SKILL_EQUIVALENCE.items():
            if s in vals:
                normalized.add(key)

    return normalized