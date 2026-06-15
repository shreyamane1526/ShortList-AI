import sys
import json

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT_DIR))

from ml.inference.context_agent.predictor import (
    predict,
)


INPUT_PATH = (
    ROOT_DIR
    / "ml"
    / "evaluation"
    / "context_agent"
    / "benchmark_inputs.json"
)

OUTPUT_PATH = (
    ROOT_DIR
    / "ml"
    / "evaluation"
    / "context_agent"
    / "predictions.json"
)


def extract_json(text):

    start = text.find("{")

    end = text.rfind("}")

    if start == -1 or end == -1:

        return None

    json_str = text[start:end + 1]

    try:

        return json.loads(json_str)

    except Exception:

        return None


def main():

    benchmark_data = json.loads(
        INPUT_PATH.read_text()
    )

    predictions = []

    for item in benchmark_data:

        print("=" * 80)

        print("Running ID:", item["id"])

        raw_output = predict(
            item["job_description"]
        )

        parsed = extract_json(
            raw_output
        )

        predictions.append(
            {
                "id": item["id"],
                "predicted_output": parsed,
            }
        )

    OUTPUT_PATH.write_text(
        json.dumps(
            predictions,
            indent=2,
        )
    )

    print()

    print(
        "Predictions saved to:",
        OUTPUT_PATH
    )


if __name__ == "__main__":

    main()