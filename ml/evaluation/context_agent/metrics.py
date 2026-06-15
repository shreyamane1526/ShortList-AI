def normalize_skill_name(skill):

    return skill.lower().strip()


def extract_skill_set(skills):

    return {
        normalize_skill_name(
            skill["name"]
        )
        for skill in skills
    }


def skill_precision_recall(
    predicted,
    expected,
):

    pred_required = extract_skill_set(
        predicted.get(
            "required_skills",
            [],
        )
    )

    exp_required = extract_skill_set(
        expected.get(
            "required_skills",
            [],
        )
    )

    true_positives = (
        pred_required &
        exp_required
    )

    precision = (
        len(true_positives)
        / max(len(pred_required), 1)
    )

    recall = (
        len(true_positives)
        / max(len(exp_required), 1)
    )

    return {
        "precision": round(
            precision,
            3,
        ),
        "recall": round(
            recall,
            3,
        ),
    }


def hallucination_rate(
    predicted,
    expected,
):

    pred_required = extract_skill_set(
        predicted.get(
            "required_skills",
            [],
        )
    )

    exp_required = extract_skill_set(
        expected.get(
            "required_skills",
            [],
        )
    )

    hallucinated = (
        pred_required -
        exp_required
    )

    rate = (
        len(hallucinated)
        / max(len(pred_required), 1)
    )

    return round(rate, 3)


def role_accuracy(
    predicted,
    expected,
):

    pred_role = (
        predicted.get(
            "role",
            "",
        )
        .lower()
        .strip()
    )

    exp_role = (
        expected.get(
            "role",
            "",
        )
        .lower()
        .strip()
    )

    return pred_role == exp_role