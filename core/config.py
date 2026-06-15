"""
core/config.py  — NEW FILE

Central settings object. Import with:
    from core.config import settings

Auto-detects:
  - Mock mode when GROQ_API_KEY is absent
  - SQLite fallback when DATABASE_URL is absent (dev convenience)
"""
from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── LLM ──────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str        = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str          = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE: float   = 0.2
    LLM_MAX_TOKENS: int      = 2000

    # ── GitHub ───────────────────────────────────────────────────────────────
    GITHUB_TOKEN: str        = os.getenv("GITHUB_TOKEN", "")
    GITHUB_BASE_URL: str     = "https://api.github.com"
    GITHUB_REQUEST_DELAY: float = 0.3

    # ── Embeddings / ChromaDB ─────────────────────────────────────────────────
    EMBEDDING_MODEL: str     = "all-MiniLM-L6-v2"
    CHROMA_COLLECTION: str   = "shortlist_jobs"
    MATCH_THRESHOLD: float   = 0.40    # cosine similarity cutoff — raised from 0.35
    # 0.55 requires genuine semantic overlap. Prevents Docker matching Git,
    # or System Design matching Linux via loose embedding proximity.

    # ── Database ──────────────────────────────────────────────────────────────
    # PostgreSQL in prod, SQLite in dev (no DATABASE_URL set)
    DATABASE_URL: str        = os.getenv(
        "DATABASE_URL", "sqlite:///./shortlist_ai.db"
    )
    CACHE_TTL_HOURS: int     = 24

    # ── API ───────────────────────────────────────────────────────────────────
    API_HOST: str            = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int            = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool              = os.getenv("DEBUG", "false").lower() == "true"

    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "shortlist-ai"
    LANGCHAIN_TRACING_V2: bool = False

    @property
    def use_mock(self) -> bool:
        """True when no Groq key is present — all agents use deterministic mocks."""
        return not bool(self.GROQ_API_KEY)

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

    @property
    def github_headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json"}
        if self.GITHUB_TOKEN:
            h["Authorization"] = f"token {self.GITHUB_TOKEN}"
        return h

    def validate_and_print(self) -> None:
        """Called once at startup — prints a clear status line for every key setting."""
        print("─" * 55)
        print("  Shortlist AI — Startup Configuration")
        print("─" * 55)
        ok   = lambda k, v: print(f"  ✓  {k:<30} {v}")
        warn = lambda k, v: print(f"  ⚠  {k:<30} {v}")

        if self.GROQ_API_KEY:
            ok("GROQ_API_KEY", f"loaded ({self.GROQ_API_KEY[:8]}...)")
        else:
            warn("GROQ_API_KEY", "NOT SET — mock mode active")

        if self.GITHUB_TOKEN:
            ok("GITHUB_TOKEN", f"loaded ({self.GITHUB_TOKEN[:8]}...)")
        else:
            warn("GITHUB_TOKEN", "not set — 60 req/hr unauthenticated")

        ok("GROQ_MODEL",         self.GROQ_MODEL)
        ok("EMBEDDING_MODEL",    self.EMBEDDING_MODEL)
        ok("MATCH_THRESHOLD",    self.MATCH_THRESHOLD)
        ok("DATABASE",           "PostgreSQL" if self.is_postgres else "SQLite (dev)")
        ok("CACHE_TTL_HOURS",    self.CACHE_TTL_HOURS)
        print("─" * 55)


settings = Settings()