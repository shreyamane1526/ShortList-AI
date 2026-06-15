NORMALIZED_SKILLS = {
    "postgres": "PostgreSQL",
    "postgre sql": "PostgreSQL",
    "fast api": "FastAPI",
    "js": "JavaScript",
    "ts": "TypeScript",
    "tf": "TensorFlow",
    "k8s": "Kubernetes",
    "ml ops": "MLOps",
}


def normalize_skill(skill: str):

    skill = skill.lower().strip()

    normalized = NORMALIZED_SKILLS.get(
        skill,
        skill.title(),
    )

    return normalized