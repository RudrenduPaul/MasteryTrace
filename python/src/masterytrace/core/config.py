"""
Project-level configuration read from `masterytrace.config.json` in the
current directory (scaffolded by `masterytrace init`). Ported from
src/core/config.ts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..models.bkt import BktConfig
from ..models.irt import IrtConfig

CONFIG_FILENAME = "masterytrace.config.json"


@dataclass
class MasteryTraceConfig:
    bkt: Optional[Dict[str, Any]] = None
    irt: Optional[Dict[str, Any]] = None


DEFAULT_CONFIG: Dict[str, Any] = {"bkt": {"fit": False}, "irt": {}}


def load_config(cwd: str) -> Dict[str, Any]:
    """
    Loads `masterytrace.config.json` from `cwd` if present, merging it
    over DEFAULT_CONFIG; otherwise returns DEFAULT_CONFIG unchanged.
    """
    config_path = Path(cwd) / CONFIG_FILENAME
    if not config_path.exists():
        return dict(DEFAULT_CONFIG)
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    merged = dict(DEFAULT_CONFIG)
    merged.update(raw)
    return merged


def bkt_config_from_dict(raw: Optional[Dict[str, Any]]) -> BktConfig:
    """Builds a BktConfig from the plain dict shape stored in masterytrace.config.json."""
    raw = raw or {}
    return BktConfig(
        default_params=raw.get("defaultParams"),
        skill_params=raw.get("skillParams"),
        fit=bool(raw.get("fit", False)),
    )


def irt_config_from_dict(raw: Optional[Dict[str, Any]]) -> IrtConfig:
    """Builds an IrtConfig from the plain dict shape stored in masterytrace.config.json."""
    raw = raw or {}
    kwargs: Dict[str, Any] = {}
    if "iterations" in raw:
        kwargs["iterations"] = raw["iterations"]
    if "learningRate" in raw:
        kwargs["learning_rate"] = raw["learningRate"]
    if "regularization" in raw:
        kwargs["regularization"] = raw["regularization"]
    return IrtConfig(**kwargs)
