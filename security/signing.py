from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any, Dict, Optional


def _deterministic_serialize(payload: Any) -> bytes:
    """Deterministic JSON serialization for signing.

    Determinism requirements:
      - sort_keys=True
      - compact separators

    Payload must be JSON-serializable.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


# IMPORTANT:
# This repo environment may not have PyNaCl installed.
# For TEE-1 we provide an Ed25519-compatible interface using
# a deterministic HMAC-SHA256 fallback for now.
#
# Once enclave keys + a real Ed25519 library are available,
# this module can be swapped without changing call sites.
#
# This keeps current inference outputs unchanged while enabling
# cryptographic-style integrity scaffolding.


def _derive_private_key(signing_key: Optional[bytes]) -> bytes:
    if signing_key is not None:
        return signing_key
    # ephemeral key (dev)
    return hashlib.sha256(os.urandom(32)).digest()


def sign_evaluation(payload: Dict[str, Any], signing_key: Optional[bytes] = None) -> Dict[str, Any]:
    """Sign an evaluation artifact (TEE-1 readiness scaffolding).

    Crypto note:
      This environment may not include a real Ed25519 implementation.
      For TEE-1 we need deterministic, *self-consistent* signing +
      verification scaffolding.

    Fallback scheme (self-verifiable):
      - seed = derive_private_key(signing_key)
      - signature = PBKDF2-HMAC-SHA256(payload, seed)
      - public_key = seed

    With public_key == seed, verify_evaluation_signature() can deterministically
    recompute the exact same signature.
    """
    serialized = _deterministic_serialize(payload)
    payload_hash = hashlib.sha256(serialized).hexdigest()

    seed = _derive_private_key(signing_key)

    sig = hashlib.pbkdf2_hmac("sha256", serialized, seed, 1, dklen=32)

    # store seed as public_key so verification can recompute the same signature
    public_key = seed

    return {
        "signature": _b64(sig),
        "public_key": _b64(public_key),
        "payload_hash": payload_hash,
    }



def verify_evaluation_signature(
    payload: Dict[str, Any],
    signature: str,
    public_key: str,
) -> bool:
    """Verify a signed evaluation artifact (fallback).

    Matches sign_evaluation() fallback scheme:
      - public_key is the seed
      - signature recomputed as PBKDF2-HMAC-SHA256(payload, seed)
    """
    serialized = _deterministic_serialize(payload)
    sig = _unb64(signature)
    seed = _unb64(public_key)

    derived = hashlib.pbkdf2_hmac("sha256", serialized, seed, 1, dklen=32)
    return derived == sig



