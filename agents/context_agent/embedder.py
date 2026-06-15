"""
agents/context_agent/embedder.py  — NEW FILE

Module 2 of 3 in Context Agent.
Responsibility: generate embeddings and manage ChromaDB storage + retrieval.

Design decisions:
  - sentence-transformers runs on CPU, no API cost
  - ChromaDB runs in-memory (no infra, no persistence needed for embeddings)
  - PostgreSQL is the source of truth; ChromaDB stores embeddings ONLY
  - Singletons loaded once per process to avoid repeated model loading
"""


from __future__ import annotations
import core.root  # ensures project root is on sys.path (Windows + Linux safe)

from typing import List, Optional, Tuple

from core.config import settings
from core.skill_mapper import normalize_skills




# def _get_model():
#     global _model
#     if _model is None:
#         import os as _os
#         # Check if model is already cached locally before attempting import
#         hf_cache = _os.path.expanduser("~/.cache/huggingface/hub")
#         model_cached = _os.path.exists(hf_cache) and any(
#             "MiniLM" in d for d in (_os.listdir(hf_cache) if _os.path.exists(hf_cache) else [])
#         )
#         if model_cached:
#             try:
#                 _os.environ["TRANSFORMERS_OFFLINE"] = "1"
#                 from sentence_transformers import SentenceTransformer
#                 _model = SentenceTransformer(settings.EMBEDDING_MODEL)
#                 print("  [Context/Embedder] Model loaded from local cache.")
#                 return _model
#             except Exception:
#                 pass
#         print("  [Context/Embedder] Model not cached — using hash embedder (run: python cache_model.py)")
#         _model = _MockEmbedder()
#     return _model


class _MockEmbedder:
    """
    Fallback embedder when sentence-transformers is not installed.
    Produces deterministic pseudo-embeddings from string hashing.
    Cosine similarity works but matches are weaker than real embeddings.
    Install sentence-transformers in production for accurate skill matching.
    """
    def encode(self, texts, convert_to_numpy=True):
        import hashlib, math
        vecs = []
        for text in texts:
            h   = hashlib.sha256(text.lower().encode()).digest()
            vec = [(b / 255.0 - 0.5) for b in h]  # 32 floats in [-0.5, 0.5]
            mag = math.sqrt(sum(v*v for v in vec)) or 1.0
            vecs.append([v/mag for v in vec])
        return vecs  # list of lists — .tolist() not needed


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        _chroma_client = chromadb.Client()
        _collection    = _chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION
        )
    return _collection


# ── Public API ─────────────────────────────────────────────────────────────────

def embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of strings. Returns list of float vectors."""
    if not texts:
        return []
    from core.models import (
        embedding_model,
    )

    model = embedding_model
    result = model.encode(texts, convert_to_numpy=True)
    # Handle both numpy arrays (.tolist()) and plain lists (from mock embedder)
    if hasattr(result, "tolist"):
        return result.tolist()
    return result  # already a list of lists


def store_jd_embedding(jd_id: str, jd_text: str, role: str, skills: List[str]) -> str:
    """
    Store a JD embedding in ChromaDB.
    Returns the doc ID (jd_id) for later retrieval.

    ChromaDB stores embeddings only — PostgreSQL stores the canonical JD data.
    """
    collection = _get_collection()
    embedding  = embed([jd_text])[0]

    # upsert so re-running the same JD doesn't duplicate
    collection.upsert(
        ids        = [jd_id],
        embeddings = [embedding],
        documents  = [jd_text],
        metadatas  = [{"role": role, "skills": ",".join(skills)}],
    )
    return jd_id


def query_similar_jds(query_text: str, n_results: int = 5) -> List[dict]:
    """
    Find similar job descriptions already stored in ChromaDB.
    Used by the Ranking Agent (Agent 4) to match candidate embeddings to jobs.
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []
    q_emb = embed([query_text])[0]
    results = collection.query(
        query_embeddings = [q_emb],
        n_results        = min(n_results, collection.count()),
    )
    return [
        {"id": doc_id, "metadata": meta, "distance": dist}
        for doc_id, meta, dist in zip(
            results["ids"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Pure-Python cosine similarity — avoids numpy in this module.
    Returns value in [0.0, 1.0].
    """
    dot   = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = sum(a * a for a in vec_a) ** 0.5
    mag_b = sum(b * b for b in vec_b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return min(1.0, dot / (mag_a * mag_b))


def match_skills(
    jd_skill_names:   List[str],
    cand_skill_names: List[str],
) -> List[Tuple[str, str, float]]:

    if not jd_skill_names:
        return []

    # 🔥 Normalize both sides
    jd_normalized   = list(normalize_skills(jd_skill_names))
    cand_normalized = list(normalize_skills(cand_skill_names))

    jd_vecs   = embed(jd_normalized)
    cand_vecs = embed(cand_normalized) if cand_normalized else []

    results = []

    for jd_skill, jd_vec in zip(jd_normalized, jd_vecs):

        best_score = 0.0
        best_match = ""

        for cand_skill, cand_vec in zip(cand_normalized, cand_vecs):

            # 🔥 1. EXACT MATCH (highest priority)
            if jd_skill == cand_skill:
                best_score = 1.0
                best_match = cand_skill
                break

            # 🔥 2. EMBEDDING MATCH
            score = cosine_similarity(jd_vec, cand_vec)

            # 🔥 Boost related backend terms
            if jd_skill in ["backend", "rest api"] and cand_skill in ["fastapi","flask","django"]:
                score = max(score, 0.8)

            if score > best_score:
                best_score = score
                best_match = cand_skill

        results.append((jd_skill, best_match, round(best_score, 3)))

    return results