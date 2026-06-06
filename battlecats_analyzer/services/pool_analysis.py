"""Pool-level analysis via teammate EV recommendation engine + optional CSV reviews."""

from __future__ import annotations

from services.gacha_explanation_engine import (
    calculate_gacha_explanation_engine,
    rank_all_pools,
)
from services.review_sections import get_review, summarize_review_bullets


def _recommendation_short(label: str) -> str:
    if label.startswith("🔥"):
        return "極度推薦"
    if label.startswith("👍"):
        return "推薦抽取"
    if label.startswith("❌"):
        return "可跳過"
    return label


def _character_explanation_item(c: dict) -> dict | None:
    review = get_review(c["id"])
    name = c.get("name") or (review or {}).get("name") or c["id"]
    grade = (c.get("tier") or {}).get("composite_grade") or c.get("grade") or ""
    head = f"{name}（{grade}）" if grade and grade != "—" else name

    if review:
        points = summarize_review_bullets(review, max_points=3)
    else:
        points = []

    if not points:
        fallback: list[str] = []
        if c.get("rarity"):
            fallback.append(str(c["rarity"]))
        score = (c.get("tier") or {}).get("composite_score")
        if score is not None:
            fallback.append(f"綜合評分 {score:.2f}")
        if not fallback:
            fallback.append("尚無評語資料")
        points = fallback

    return {
        "head": head,
        "name": name,
        "grade": grade if grade and grade != "—" else "",
        "points": points,
        "id": c["id"],
    }


def _build_review_explanations(characters: list[dict]) -> tuple[dict, list[dict]]:
    ranked = sorted(
        characters,
        key=lambda c: (
            -((c.get("tier") or {}).get("composite_score") or 0),
            c.get("name") or c["id"],
        ),
    )

    items: list[dict] = []
    for c in ranked:
        item = _character_explanation_item(c)
        if item:
            items.append(item)

    s_count = sum(
        1 for c in characters if (c.get("tier") or {}).get("composite_grade") == "S"
    )
    summary = {
        "head": "角色短評（CSV）",
        "points": [f"共 {len(characters)} 隻 SSR/SSSR", f"S 等第 {s_count} 隻"],
    }
    return summary, items


def analyze_pool(pool_key: str, owned_ids: list[str] | None = None, *, characters: list[dict] | None = None) -> dict:
    """Run EV engine for pool_key + owned_ids; attach optional per-character CSV reviews."""
    engine = calculate_gacha_explanation_engine(pool_key, owned_ids or [])

    if engine.get("status") != "success":
        return {
            "status": "error",
            "message": engine.get("message", "分析失敗"),
            "pool_key": pool_key,
        }

    metrics = engine["metrics"]
    recommendation = metrics["recommendation_level"]
    stats = metrics["stats"]
    explanations = engine["display_explanations"]
    pockets = engine["pockets"]
    thresholds = metrics["thresholds"]

    rankings = rank_all_pools(owned_ids or [])
    pool_rank = None
    for row in rankings["rows"]:
        if row["pool_name"] == pool_key:
            pool_rank = row["rank"]
            break

    review_summary = None
    review_visible: list[dict] = []
    review_hidden: list[dict] = []
    review_has_more = False
    review_hidden_count = 0

    if characters:
        review_summary, review_items = _build_review_explanations(characters)
        visible_count = 5
        review_visible = review_items[:visible_count]
        review_hidden = review_items[visible_count:]
        review_has_more = len(review_items) > visible_count
        review_hidden_count = max(0, len(review_items) - visible_count)

    return {
        "status": "success",
        "pool_key": pool_key,
        "recommendation_level": recommendation,
        "recommendation_short": _recommendation_short(recommendation),
        "skip_reason_type": metrics["skip_reason_type"],
        "skip_reason_label": metrics.get("skip_reason_label", ""),
        "ev_initial": metrics["ev_initial"],
        "ev_current": metrics["ev_current"],
        "thresholds": thresholds,
        "stats": stats,
        "pockets": pockets,
        "display_explanations": explanations,
        "character_roster": engine.get("character_roster", []),
        "ssr_roster": engine.get("ssr_roster", []),
        "sssr_roster": engine.get("sssr_roster", []),
        "pool_rank": pool_rank,
        "total_pools": rankings["total_pools"],
        "rankings_preview": rankings["rows"][:15],
        "rankings_thresholds": rankings["thresholds"],
        "data_sources": [
            "角色強度：data/battlecats_final_tier_list.csv 的「綜合評分」（0–5）",
            "  └ 訓練：DA_ML_rare_model.ipynb — XGBoost 以模組分 + SSR/SSSR 特徵預測；有人工標籤者保留真實分，其餘用預測分",
            "陣容模組分：data/module_scores_export.csv（0–10）",
            "  └ 訓練：battle_cats_ml_test3 — 爬蟲 JSON 抽特徵 → scoring.py 三模組加權 → min-max 縮放",
            "卡池成員：data/gacha_pool_characters_mapping.json 的 SSR / SSSR 清單",
            f"抽卡機率假設：SSR 單抽 {thresholds['p_ssr_pct']} 均分池內 {stats['total_ssr']} 隻（每隻 {thresholds['p_ssr']:.6f}）；"
            f"SSSR 單抽 {thresholds['p_sssr_pct']} 均分 {stats['total_sssr']} 隻（每隻 {thresholds['p_sssr']:.6f}）",
            "初始期望值 ev_initial = Σ(機率 × 綜合評分)；當前期望值 ev_current = 未擁有角色貢獻加總",
            f"推薦門檻：PR40={thresholds['pr40']} · PR80={thresholds['pr80']}（DA_ML_PoolScore 全零持有 baseline）",
            "分級口袋：神級 ≥4.3 · S 級 3.75–4.3 · A 級 3.25–3.75 · 其餘視為弱勢/倉管",
        ],
        "review_summary": review_summary,
        "review_visible": review_visible,
        "review_hidden": review_hidden,
        "review_has_more": review_has_more,
        "review_hidden_count": review_hidden_count,
    }
