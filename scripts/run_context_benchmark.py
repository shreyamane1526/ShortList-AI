import json

from pathlib import Path

from ml.inference.context_agent.predictor import (
    predict,
)


INPUT_PATH = (
    "ml/evaluation/context_agent/"
    "benchmark_inputs.json"
)


def main():

    data = json.loads(
        Path(INPUT_PATH).read_text()
    )

    for item in data:

        print("=" * 80)

        print("ID:", item["id"])

        print()

        result = predict(
            item["job_description"]
        )

        print(result)

        print()


if __name__ == "__main__":

    main()