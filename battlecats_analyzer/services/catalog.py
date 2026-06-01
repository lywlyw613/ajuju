"""Load characters, gacha pool, ML scores — all from ajuju_mission data."""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

from config import DATA_JSON, GACHA_JSON, ML_DIR, SKIP_ML_BUILD, unit_image_url
from services.analysis import build_ai_analysis
from services.roster_analysis import get_module_score

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from data_io import pick_form  # noqa: E402
from display_utils import list_active_abilities  # noqa: E402
from game_labels import ABILITY_NAME_CN  # noqa: E402

_catalog: dict | None = None
_gacha: dict[str, str] | None = None
_scores_by_id: dict[str, dict] | None = None


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _rating_to_display(rating) -> float | None:
    if rating in (None, "", "NAN", "nan"):
        return None
    try:
        return round(max(0.0, min(4.5, float(rating))) / 4.5 * 10.0, 1)
    except (TypeError, ValueError):
        return None


def _ability_tags(form: dict) -> list[str]:
    tags: list[str] = []
    abilities = form.get("能力", {})
    if not isinstance(abilities, dict):
        return tags
    for ab in abilities.values():
        if not isinstance(ab, dict) or not ab.get("有此能力"):
            continue
        aid = int(ab.get("能力ID", 0))
        name = ABILITY_NAME_CN.get(aid)
        if name and name not in tags:
            tags.append(name)
    return tags[:12]


def _safe_num(val, default=0):
    if val in (None, "", "NAN", "nan"):
        return default
    try:
        return val if isinstance(val, (int, float)) else float(val)
    except (TypeError, ValueError):
        return default


def _collect_name_info(char: dict, form: dict | None) -> dict:
    primary = (form or {}).get("名字", "") if form else ""
    names: list[str] = []
    for key in (
        "一階資料",
        "二階資料",
        "三階資料",
        "四階資料",
        "三階滿本能",
        "四階滿本能",
    ):
        v = char.get(key)
        if isinstance(v, dict):
            n = v.get("名字")
            if n and n not in (None, "", "NAN", "nan") and n not in names:
                names.append(str(n))
    base = ""
    s1 = char.get("一階資料")
    if isinstance(s1, dict) and s1.get("名字") not in (None, "", "NAN", "nan"):
        base = str(s1["名字"])
    other = [n for n in names if n != primary and n != base]
    return {
        "name": primary or base or "",
        "name_jp": primary or base or "",
        "name_base": base,
        "name_other": other,
        "all_names": names,
        "search_text": " ".join(names).lower(),
    }


def _char_summary(cat_id: str, char: dict, pool_rarity: str | None = None) -> dict | None:
    stage, form = pick_form(char)
    if not form:
        return None
    cid = cat_id.zfill(3)
    names = _collect_name_info(char, form)
    name = names["name"] or cid
    rating = char.get("評分")
    display_score = _rating_to_display(rating)
    csv_row = get_module_score(cid)
    if csv_row and csv_row.get("display_score") is not None:
        display_score = csv_row["display_score"]
    row = (_scores_by_id or {}).get(cid, {})
    if display_score is None and row:
        for key in ("score_mod1", "pred_m1_評分"):
            if key in row and row[key] is not None:
                try:
                    v = float(row[key])
                    display_score = round(v if v <= 10 else v / 4.5 * 10, 1)
                    break
                except (TypeError, ValueError):
                    pass
    if display_score is None:
        display_score = round(
            (
                float(row.get("score_mod1", 5) or 5)
                + float(row.get("score_mod2", 5) or 5)
                + float(row.get("score_mod3", 5) or 5)
            )
            / 3,
            1,
        )

    return {
        "id": cid,
        "name": name,
        "name_jp": names["name_jp"],
        "name_base": names["name_base"],
        "name_other": names["name_other"],
        "all_names": names["all_names"],
        "search_text": names["search_text"],
        "rarity": pool_rarity or _infer_rarity(cat_id),
        "score": display_score,
        "module_csv": csv_row,
        "image_url": unit_image_url(cat_id),
        "form_stage": stage,
    }


def _infer_rarity(cat_id: str) -> str:
    g = _gacha or {}
    return g.get(cat_id.zfill(3), g.get(cat_id.lstrip("0") or "0", "N"))


def _build_scores(raw: dict) -> dict[str, dict]:
    if SKIP_ML_BUILD:
        return {}
    try:
        from features import build_feature_dataframe

        with contextlib.redirect_stdout(io.StringIO()):
            df = build_feature_dataframe(raw)
        if df.empty:
            return {}
        return {str(r["角色鍵"]).zfill(3): r.to_dict() for _, r in df.iterrows()}
    except Exception:
        return {}


def get_catalog() -> dict[str, dict]:
    global _catalog, _gacha, _scores_by_id
    if _catalog is not None:
        return _catalog

    raw = _load_json(DATA_JSON)
    _gacha = _load_json(GACHA_JSON)
    _scores_by_id = _build_scores(raw)

    _catalog = {}
    for cat_id, char in raw.items():
        if not isinstance(char, dict):
            continue
        summary = _char_summary(str(cat_id), char)
        if summary:
            _catalog[summary["id"]] = {"raw": char, "summary": summary}
    return _catalog


def get_gacha_pool(query: str = "") -> list[dict]:
    gacha = _gacha or _load_json(GACHA_JSON)
    catalog = get_catalog()
    pool = []
    q = (query or "").strip().lower()
    for cat_id, rarity in gacha.items():
        if rarity not in ("SSR", "SSSR"):
            continue
        cid = str(cat_id).zfill(3)
        entry = catalog.get(cid)
        if not entry:
            continue
        s = dict(entry["summary"])
        s["rarity"] = rarity
        if q:
            hay = f"{s['id']} {s.get('search_text', '')} {s.get('name', '')}".lower()
            if q not in hay and q not in s["id"].lstrip("0"):
                continue
        pool.append(s)
    pool.sort(key=lambda x: (0 if x["rarity"] == "SSSR" else 1, -(x.get("score") or 0)))
    return pool


def get_carousel_slides(n: int = 5) -> list[dict]:
    pool = get_gacha_pool()
    return pool[:n] if pool else []


def search_characters(query: str = "") -> list[dict]:
    catalog = get_catalog()
    items = [c["summary"] for c in catalog.values()]
    q = (query or "").strip().lower()
    if not q:
        return sorted(items, key=lambda x: x["name"])[:80]
    matched = [
        s
        for s in items
        if q in s.get("search_text", s["name"].lower())
        or q in s["name"].lower()
        or q in s["id"]
        or q in s["id"].lstrip("0")
    ]
    return sorted(matched, key=lambda x: x["name"])[:50]


def _module_scores_for_detail(cid: str, row: dict) -> dict:
    csv_row = get_module_score(cid)
    if csv_row:
        return {
            "mod1": round(float(csv_row.get("mod1") or 0), 1),
            "mod2": round(float(csv_row.get("mod2") or 0), 1),
            "mod3": round(float(csv_row.get("mod3") or 0), 1),
        }
    return {
        "mod1": round(float(row.get("score_mod1", 0) or 0), 1),
        "mod2": round(float(row.get("score_mod2", 0) or 0), 1),
        "mod3": round(float(row.get("score_mod3", 0) or 0), 1),
    }


def get_character_detail(cat_id: str) -> dict | None:
    catalog = get_catalog()
    cid = str(cat_id).zfill(3)
    entry = catalog.get(cid)
    if not entry:
        return None

    char = entry["raw"]
    stage, form = pick_form(char)
    if not form:
        return None

    row = (_scores_by_id or {}).get(cid, {})
    summary = dict(entry["summary"])
    summary["rarity"] = _gacha.get(cid, summary.get("rarity", "N")) if _gacha else summary.get("rarity")

    ai = build_ai_analysis(char, form, row)
    abilities_text = list_active_abilities(form.get("能力", {}))

    return {
        **summary,
        "form_stage": stage,
        "stats": {
            "體力": _safe_num(form.get("體力")),
            "KB": _safe_num(form.get("KB")),
            "速度": _safe_num(form.get("速度")),
            "DPS": _safe_num(form.get("DPS")),
            "射程": _safe_num(form.get("射程")),
            "範圍": form.get("範圍", "—"),
            "成本": _safe_num(form.get("成本")),
            "攻擊頻率": _safe_num(form.get("攻擊頻率")),
            "再生產": _safe_num(form.get("再生產")),
        },
        "ability_tags": _ability_tags(form),
        "abilities_text": abilities_text,
        "module_scores": _module_scores_for_detail(cid, row),
        "ai": ai,
        "trait": row.get("針對屬性", "無"),
    }
