from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path | None = None) -> dict:
    p = Path(path) if path else ROOT / "config.toml"
    with open(p, "rb") as f:
        return tomllib.load(f)


def find_font(candidates: list[str]) -> str | None:
    for c in candidates:
        if Path(c).is_file():
            return c
    return None
