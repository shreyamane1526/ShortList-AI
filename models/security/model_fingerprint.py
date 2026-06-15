from __future__ import annotations

import hashlib
import json
from typing import Any, Optional


def _sha256_hexdigest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    """Deterministic SHA256 over a JSON-serializable object."""
    normalized = normalize_for_json(value)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_hexdigest(payload)


def normalize_for_json(value: Any) -> Any:
    """Best-effort normalization for deterministic hashing.

    - dict: recurse
    - list/tuple: recurse
    - pydantic models / objects: if they have model_dump(), use it
    - otherwise: return value as-is
    """
    if value is None:
        return None

    # pydantic
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return normalize_for_json(value.model_dump(mode="json"))

    if hasattr(value, "dict") and callable(value.dict):
        try:
            return normalize_for_json(value.dict())
        except TypeError:
            pass

    if isinstance(value, dict):
        return {str(k): normalize_for_json(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [normalize_for_json(v) for v in value]

    return value


def compute_model_hash(model_bytes: Optional[bytes] = None, model_path: Optional[str] = None) -> str:
    """Compute SHA256 over the ranking model artifact.

    TEE-1 keeps this logic generic because the repo may store/serialize the model
    in different ways during dev.
    Provide either model_bytes or model_path.
    """
    if model_bytes is None and model_path is None:
        # stable sentinel
        return _sha256_hexdigest(b"model-not-provided")

    if model_bytes is not None and model_path is not None:
        raise ValueError("Provide only one of model_bytes or model_path")

    if model_bytes is not None:
        return _sha256_hexdigest(model_bytes)

    # model_path
    with open(model_path, "rb") as f:
        return _sha256_hexdigest(f.read())


def compute_feature_schema_hash(feature_schema: dict | Any) -> str:
    """Compute SHA256 over feature schema dictionary."""
    return sha256_json(feature_schema)


def compute_prompt_hash(prompt: dict | str | Any) -> str:
    """Compute SHA256 over prompt template/text."""
    return sha256_json(prompt)

