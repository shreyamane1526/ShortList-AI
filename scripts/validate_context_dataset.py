import sys
from pathlib import Path

# Add project root to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT_DIR))

import json

from agents.context_agent.validator import (
    validate_dataset_entry,
)

DATASET_PATH = (
    ROOT_DIR
    / "ml"
    / "datasets"
    / "context_agent"
    / "labeled"
    / "gold_labels.json"
)


def main():

    data = json.loads(
        DATASET_PATH.read_text()
    )

    valid = 0
    invalid = 0

    for entry in data:

        if validate_dataset_entry(entry):
            valid += 1
        else:
            invalid += 1

    print("Valid:", valid)

    print("Invalid:", invalid)


if __name__ == "__main__":
    main()