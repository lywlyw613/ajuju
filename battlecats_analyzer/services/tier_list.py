"""Load battlecats_final_tier_list.csv — scores and letter grades by character ID."""

from __future__ import annotations

import csv
from pathlib import Path

from config import TIER_LIST_CSV

_cache: dict[str, dict] | None = None


def _parse_float(val) -> float | None:
    if val in (None, "", "NAN", "nan"):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def score_to_stars(score: float | None) -> tuple[int, str]:
    """Map 0–5 composite score to filled star count and display string."""
    if score is None:
        return 0, "—"
    filled = max(1, min(5, round(score)))
    empty = 5 - filled
    return filled, ("★" * filled) + ("☆" * empty)


def load_tier_list() -> dict[str, dict]:
    global _cache
    if _cache is not None:
        return _cache

    out: dict[str, dict] = {}
    if not TIER_LIST_CSV.is_file():
        _cache = out
        return out

    with open(TIER_LIST_CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = str(row.get("ID", "")).strip().zfill(3)
            if not cid or cid == "000":
                continue

            composite = _parse_float(row.get("綜合評分"))
            stars_n, stars = score_to_stars(composite)

            out[cid] = {
                "id": cid,
                "name": (row.get("名字") or "").strip(),
                "rarity": (row.get("稀有度") or "").strip(),
                "composite_score": composite,
                "composite_grade": (row.get("綜合等第") or "").strip(),
                "real_score": _parse_float(row.get("真實評分")),
                "real_grade": (row.get("真實等第") or "").strip(),
                "pred_score": _parse_float(row.get("預測評分")),
                "pred_grade": (row.get("預測等第") or "").strip(),
                "stars": stars,
                "stars_count": stars_n,
            }

    _cache = out
    return out


def get_tier(cat_id: str) -> dict | None:
    return load_tier_list().get(str(cat_id).zfill(3))
