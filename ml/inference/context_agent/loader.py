from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

from peft import PeftModel


BASE_MODEL = (
    "microsoft/Phi-3-mini-4k-instruct"
)

ADAPTER_PATH = (
    "ml/adapters/context_agent"
)


def load_context_agent():

    tokenizer = (
        AutoTokenizer.from_pretrained(
            BASE_MODEL
        )
    )

    base_model = (
        AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            device_map="cpu",
        )
    )

    model = PeftModel.from_pretrained(
        base_model,
        ADAPTER_PATH,
    )

    return model, tokenizer