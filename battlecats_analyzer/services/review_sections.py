"""Load id_review_sections_export.csv — narrative analysis per character ID."""

from __future__ import annotations

import csv
from pathlib import Path

from config import REVIEW_SECTIONS_CSV

_cache: dict[str, dict] | None = None


def load_reviews() -> dict[str, dict]:
    global _cache
    if _cache is not None:
        return _cache

    out: dict[str, dict] = {}
    if not REVIEW_SECTIONS_CSV.is_file():
        _cache = out
        return out

    with open(REVIEW_SECTIONS_CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = str(row.get("角色ID", "")).strip().zfill(3)
            if not cid or cid == "000":
                continue
            out[cid] = {
                "id": cid,
                "name": (row.get("名字") or "").strip(),
                "versatility": (row.get("泛用性評估") or "").strip(),
                "tactics": (row.get("功能定位與戰術價值") or "").strip(),
                "training": (row.get("培養建議") or "").strip(),
            }

    _cache = out
    return out


def get_review(cat_id: str) -> dict | None:
    return load_reviews().get(str(cat_id).zfill(3))


def build_explanation_snippet(review: dict | None, char_name: str = "") -> list[str]:
    """Turn review sections into bullet-style explanation lines."""
    if not review:
        return []
    lines: list[str] = []
    label = char_name or review.get("name") or "此角色"
    if review.get("versatility"):
        lines.append(f"{label}：{review['versatility']}")
    if review.get("tactics"):
        lines.append(review["tactics"])
    if review.get("training"):
        lines.append(review["training"])
    return lines
