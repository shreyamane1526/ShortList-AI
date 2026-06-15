import json
import torch

from ml.inference.context_agent.loader import (
    load_context_agent,
)

from ml.inference.context_agent.prompts import (
    SYSTEM_PROMPT,
)


model, tokenizer = (
    load_context_agent()
)


def build_prompt(job_description):

    return f"""
<|system|>
{SYSTEM_PROMPT}

<|user|>
{job_description}

<|assistant|>
"""


def predict(job_description):

    prompt = build_prompt(
        job_description
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    ).to("cpu")

    with torch.no_grad():

        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.1,
        )

    decoded = tokenizer.decode(
        outputs[0],
        skip_special_tokens=True,
    )

    return decoded