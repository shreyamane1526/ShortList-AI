"""
Shared singleton AI models.

All heavyweight models should load ONLY ONCE here.
"""

from __future__ import annotations

from sentence_transformers import (
    SentenceTransformer,
)

from groq import Groq

from core.config import settings


print(
    "\n[Model Registry] Loading shared models..."
)

# ─────────────────────────────────────────────────────
# Embedding model singleton
# ─────────────────────────────────────────────────────

embedding_model = SentenceTransformer(
    settings.EMBEDDING_MODEL
)

print(
    f"[Model Registry] "
    f"Embedding model loaded: "
    f"{settings.EMBEDDING_MODEL}"
)

# ─────────────────────────────────────────────────────
# Shared Groq client
# ─────────────────────────────────────────────────────

groq_client = Groq(
    api_key=settings.GROQ_API_KEY
)

print(
    "[Model Registry] Groq client initialized"
)

print(
    "[Model Registry] READY\n"
)