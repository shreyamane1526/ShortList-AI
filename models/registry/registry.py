"""Model registry utilities.

Production goal: centralize reading/writing of:
- per-version metadata artifacts (xgb_model_v{N}.json)
- active model pointer (models/current_model.json)

IMPORTANT: This module is designed to be a *behavior-preserving* refactor
for existing training/retraining logic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class ModelPaths:
    model_dir: Path
    registry_dir: Path
    current_model_path: Path

    @staticmethod
    def from_repo_root(project_root: Path) -> "ModelPaths":
        model_dir = project_root / "models"
        registry_dir = model_dir / "registry"
        current_model_path = model_dir / "current_model.json"
        return ModelPaths(
            model_dir=model_dir,
            registry_dir=registry_dir,
            current_model_path=current_model_path,
        )


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_registered_model_versions(registry_dir: Path) -> list[int]:
    """Return sorted integer versions discovered in registry_dir."""
    versions: list[int] = []
    if not registry_dir.exists():
        return versions

    for p in registry_dir.glob("xgb_model_v*.json"):
        # xgb_model_v{N}.json
        stem = p.stem
        suffix = stem.replace("xgb_model_v", "")
        if suffix.isdigit():
            versions.append(int(suffix))

    return sorted(set(versions))


def read_model_metadata_by_version(model_paths: ModelPaths, version: int) -> dict[str, Any]:
    metadata_path = model_paths.registry_dir / f"xgb_model_v{version}.json"
    return _safe_read_json(metadata_path)


def write_current_model(model_paths: ModelPaths, *, version: int, metadata: dict[str, Any]) -> None:
    """Write pointer file to current_model.json.

    Behavior note: retrain.py currently writes the *same metadata json* into
    current_model.json on promotion. We preserve that exact semantics.
    """
    model_paths.model_dir.mkdir(parents=True, exist_ok=True)
    # Preserve existing behavior: current_model.json content equals metadata
    payload = json.dumps(metadata, indent=2)
    model_paths.current_model_path.write_text(payload, encoding="utf-8")


def ensure_registry_dirs(model_paths: ModelPaths) -> None:
    model_paths.registry_dir.mkdir(parents=True, exist_ok=True)


def now_utc_iso() -> str:
    return datetime.utcnow().isoformat()

