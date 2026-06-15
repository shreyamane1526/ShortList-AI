import sys
import json
import random

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT_DIR))


INPUT_PATH = (
    ROOT_DIR
    / "ml"
    / "datasets"
    / "context_agent"
    / "labeled"
    / "gold_labels.json"
)

OUTPUT_DIR = (
    ROOT_DIR
    / "ml"
    / "datasets"
    / "context_agent"
)


SYSTEM_PROMPT = (
    "Extract structured hiring requirements "
    "from job descriptions. "
    "Return ONLY valid JSON."
)


def convert_entry(entry):

    return {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": entry["job_description"],
            },
            {
                "role": "assistant",
                "content": json.dumps(
                    entry["output"]
                ),
            },
        ]
    }


def write_jsonl(path, rows):

    with open(path, "w") as f:

        for row in rows:

            f.write(
                json.dumps(row)
                + "\n"
            )


def main():

    data = json.loads(
        INPUT_PATH.read_text()
    )

    converted = [
        convert_entry(entry)
        for entry in data
    ]

    random.shuffle(converted)

    total = len(converted)

    train_end = int(total * 0.8)

    val_end = int(total * 0.9)

    train = converted[:train_end]

    val = converted[train_end:val_end]

    test = converted[val_end:]

    write_jsonl(
        OUTPUT_DIR / "train.jsonl",
        train,
    )

    write_jsonl(
        OUTPUT_DIR / "val.jsonl",
        val,
    )

    write_jsonl(
        OUTPUT_DIR / "test.jsonl",
        test,
    )

    print("Train:", len(train))

    print("Validation:", len(val))

    print("Test:", len(test))


if __name__ == "__main__":
    main()