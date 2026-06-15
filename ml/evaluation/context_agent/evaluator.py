import json

from pathlib import Path

from ml.evaluation.context_agent.metrics import (
    skill_precision_recall,
    hallucination_rate,
    role_accuracy,
)


EXPECTED_PATH = (
    "ml/evaluation/context_agent/"
    "benchmark_expected.json"
)

PREDICTIONS_PATH = (
    "ml/evaluation/context_agent/"
    "predictions.json"
)


def main():

    expected = json.loads(
        Path(EXPECTED_PATH).read_text()
    )

    predictions = json.loads(
        Path(PREDICTIONS_PATH).read_text()
    )

    total_precision = 0
    total_recall = 0
    total_hallucination = 0
    total_role_accuracy = 0

    total = len(expected)

    pred_map = {
        item["id"]: item
        for item in predictions
    }

    for exp in expected:

        pred = pred_map.get(
            exp["id"]
        )

        if not pred:
            continue

        predicted_output = (
            pred["predicted_output"]
        )

        expected_output = (
            exp["expected_output"]
        )

        pr = skill_precision_recall(
            predicted_output,
            expected_output,
        )

        hallucination = hallucination_rate(
            predicted_output,
            expected_output,
        )

        role_match = role_accuracy(
            predicted_output,
            expected_output,
        )

        total_precision += pr[
            "precision"
        ]

        total_recall += pr[
            "recall"
        ]

        total_hallucination += (
            hallucination
        )

        total_role_accuracy += int(
            role_match
        )

    print("=" * 80)

    print(
        "Average Precision:",
        round(
            total_precision / total,
            3,
        ),
    )

    print(
        "Average Recall:",
        round(
            total_recall / total,
            3,
        ),
    )

    print(
        "Hallucination Rate:",
        round(
            total_hallucination
            / total,
            3,
        ),
    )

    print(
        "Role Accuracy:",
        round(
            total_role_accuracy
            / total,
            3,
        ),
    )


if __name__ == "__main__":

    main()