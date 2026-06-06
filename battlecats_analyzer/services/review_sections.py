"""Load id_review_sections_export.csv — narrative analysis per character ID."""

from __future__ import annotations

import csv
import re
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


def _clean_text(text: str) -> str:
    text = re.sub(r"[【】<>]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _first_clause(text: str, max_len: int = 20) -> str:
    if not text:
        return ""
    text = _clean_text(text)
    for sep in "。；":
        if sep in text:
            text = text.split(sep)[0]
            break
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _versatility_tag(text: str) -> str:
    if not text:
        return ""
    if "極高" in text or "優秀" in text:
        return "泛用性高"
    if "中規中矩" in text:
        return "泛用性中等"
    if "偏低" in text or "不足" in text:
        return "泛用性偏低"
    return _first_clause(text, 14)


def _tactics_tag(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"【([^】]+)】", text)
    if m:
        role = m.group(1).replace("。", "").strip()
        return role[:16]
    if "控場" in text:
        return "控場型"
    if "特化" in text:
        return "屬性特化"
    if "倉庫" in text:
        return "倉庫位"
    return _first_clause(text, 14)


def _training_tag(text: str) -> str:
    if not text:
        return ""
    if "強烈" in text or "極高" in text:
        return "優先培養"
    if "不推薦" in text or "極低" in text:
        return "不建議抽"
    if "中等" in text or "適當" in text:
        return "視需求培養"
    if "偏高" in text:
        return "值得培養"
    return _first_clause(text, 14)


def summarize_review_bullets(review: dict | None, max_points: int = 3) -> list[str]:
    """Condense review CSV fields into short bullet phrases."""
    if not review:
        return []
    raw = [
        _versatility_tag(review.get("versatility", "")),
        _tactics_tag(review.get("tactics", "")),
        _training_tag(review.get("training", "")),
    ]
    points: list[str] = []
    for tag in raw:
        if tag and tag not in points:
            points.append(tag)
        if len(points) >= max_points:
            break
    return points
