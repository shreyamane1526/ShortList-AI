"""Portfolio / PDF resume collector — unchanged from Agent 1."""
from __future__ import annotations
import io
import httpx
from bs4 import BeautifulSoup
from .base import BaseCollector

TAGS     = ["p","h1","h2","h3","li"]
CLASSES  = {"skill","about","project","experience","work","bio","summary"}


class PortfolioCollector(BaseCollector):
    platform_name = "portfolio"

    async def collect(self, url: str) -> dict:
        is_pdf = url.lower().endswith(".pdf")
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                if "pdf" in resp.headers.get("content-type", ""):
                    is_pdf = True
                raw = resp.content
        except Exception as e:
            return {"type": "unknown", "text": "", "error": str(e)}
        return _pdf(raw) if is_pdf else _html(raw)


def _pdf(raw: bytes) -> dict:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        return {"type": "resume", "text": text[:5000], "error": None}
    except Exception as e:
        return {"type": "resume", "text": "", "error": str(e)}


def _html(raw: bytes) -> dict:
    try:
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script","style","nav","footer","head"]):
            tag.decompose()
        parts = []
        for tag in soup.find_all(TAGS):
            t = tag.get_text(separator=" ", strip=True)
            if t: parts.append(t)
        for el in soup.find_all(True):
            cls = " ".join(el.get("class",[])).lower()
            eid = (el.get("id") or "").lower()
            if any(kw in cls or kw in eid for kw in CLASSES):
                t = el.get_text(separator=" ", strip=True)
                if t and t not in parts: parts.append(t)
        return {"type": "portfolio", "text": " ".join(parts)[:5000], "error": None}
    except Exception as e:
        return {"type": "portfolio", "text": "", "error": str(e)}