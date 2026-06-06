"""Team roster / lineup scoring from module_scores_export.csv."""

from __future__ import annotations

import csv
from pathlib import Path

from config import MODULE_SCORES_CSV

_GRADE_FROM_SCORE = [(9.0, "S"), (7.5, "A"), (5.5, "B"), (0.0, "C")]

MODULE_LABELS = {
    "mod1": "面板白質評分",
    "mod2": "屬性特化評分",
    "mod3": "屬性控場評分",
}

_scores_cache: dict[str, dict] | None = None


def _grade_from_number(score: float | None) -> str:
    if score is None:
        return "—"
    for threshold, letter in _GRADE_FROM_SCORE:
        if score >= threshold:
            return letter
    return "C"


def load_module_scores() -> dict[str, dict]:
    global _scores_cache
    if _scores_cache is not None:
        return _scores_cache

    out: dict[str, dict] = {}
    if not MODULE_SCORES_CSV.is_file():
        _scores_cache = out
        return out

    with open(MODULE_SCORES_CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = str(row.get("角色ID", "")).strip().zfill(3)
            if not cid:
                continue

            def _f(key: str):
                v = (row.get(key) or "").strip()
                if not v:
                    return None
                try:
                    return float(v)
                except ValueError:
                    return None

            m1, m2, m3 = _f("模組1分數"), _f("模組2分數"), _f("模組3分數")
            g1 = (row.get("模組1等第") or "").strip() or _grade_from_number(m1)
            g2 = (row.get("模組2等第") or "").strip() or _grade_from_number(m2)
            g3 = (row.get("模組3等第") or "").strip() or _grade_from_number(m3)

            overall = None
            parts = [x for x in (m1, m2, m3) if x is not None]
            if parts:
                overall = round(sum(parts) / len(parts), 2)

            out[cid] = {
                "mod1": m1,
                "mod2": m2,
                "mod3": m3,
                "grade1": g1,
                "grade2": g2,
                "grade3": g3,
                "overall": overall,
                "display_score": round(overall, 1) if overall is not None else None,
            }

    _scores_cache = out
    return out


def get_module_score(cat_id: str) -> dict | None:
    return load_module_scores().get(str(cat_id).zfill(3))


def analyze_roster(selected_ids: list[str]) -> dict:
    scores = load_module_scores()
    selected = [str(i).zfill(3) for i in selected_ids if str(i).strip()]
    members: list[dict] = []
    missing: list[str] = []

    for cid in selected:
        row = scores.get(cid)
        if not row:
            missing.append(cid)
            continue
        members.append({"id": cid, **row})

    if not members:
        return {
            "count": 0,
            "selected_count": len(selected),
            "missing": missing,
            "members": [],
            "summary": "請至少勾選一隻在模組分資料表內有紀錄的角色。",
            "averages": {},
            "grade_counts": {},
            "tier": "—",
            "lineup_score_label": "—",
            "module_rows": [],
            "mod_notes": [],
        }

    def _avg(key: str) -> float | None:
        vals = [m[key] for m in members if m.get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    avgs = {
        "mod1": _avg("mod1"),
        "mod2": _avg("mod2"),
        "mod3": _avg("mod3"),
        "overall": _avg("overall"),
    }

    grade_counts: dict[str, int] = {"S": 0, "A": 0, "B": 0, "C": 0}
    for m in members:
        for gk in ("grade1", "grade2", "grade3"):
            g = m.get(gk, "")
            if g in grade_counts:
                grade_counts[g] += 1

    overall = avgs["overall"] or 0
    if overall >= 8:
        tier = "頂尖"
        summary = "整體陣容極強，三項模組平均表現優秀，適合多數高難關。"
    elif overall >= 7:
        tier = "強勢"
        summary = "陣容強度良好，建議補齊屬性控場或特化短板。"
    elif overall >= 5.5:
        tier = "中等"
        summary = "陣容可用但仍有缺口，可優先補強評分較低的模組。"
    else:
        tier = "待加強"
        summary = "目前陣容平均模組分偏低，建議逐步替換為高分角色。"

    module_rows = []
    mod_notes = []
    for key in ("mod1", "mod2", "mod3"):
        avg = avgs[key]
        label = MODULE_LABELS[key]
        grade = _grade_from_number(avg)
        module_rows.append({"key": key, "label": label, "avg": avg, "grade": grade})
        if avg is not None:
            mod_notes.append(f"{label} 平均 {avg:.2f}，等第約 {grade}")

    lineup_score_label = f"{overall:.2f} / 10" if avgs["overall"] is not None else "—"

    return {
        "count": len(members),
        "selected_count": len(selected),
        "missing": missing,
        "members": sorted(members, key=lambda x: -(x.get("overall") or 0)),
        "averages": avgs,
        "grade_counts": grade_counts,
        "tier": tier,
        "summary": summary,
        "mod_notes": mod_notes,
        "module_rows": module_rows,
        "lineup_score_label": lineup_score_label,
    }
