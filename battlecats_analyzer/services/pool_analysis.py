"""Pool-level analysis: Pool Score, Recommendation, Explanation.

Pool Score and Recommendation use mock formulas until backend models are ready.
Explanation pulls from id_review_sections_export.csv for top characters in pool.
"""

from __future__ import annotations

from services.review_sections import get_review, summarize_review_bullets


def _mock_pool_score(characters: list[dict]) -> float:
    """0–100 mock score from average composite tier score (0–5)."""
    scores = [
        c["tier"]["composite_score"]
        for c in characters
        if c.get("tier") and c["tier"].get("composite_score") is not None
    ]
    if not scores:
        return 72.0
    avg = sum(scores) / len(scores)
    return round(avg / 5.0 * 100, 1)


def _mock_recommendation(pool_score: float) -> str:
    if pool_score >= 88:
        return "強烈推薦抽取"
    if pool_score >= 78:
        return "建議抽取"
    if pool_score >= 65:
        return "可視需求抽取"
    return "觀望為宜"


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
            fallback.append(f"評分 {score:.2f}")
        if not fallback:
            fallback.append("尚無評語資料")
        points = fallback

    return {"head": head, "points": points, "id": c["id"]}


def _build_explanation_items(characters: list[dict]) -> tuple[dict, list[dict]]:
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
        "head": "卡池概況",
        "points": [f"共 {len(characters)} 隻 SSR/SSSR", f"S 等第 {s_count} 隻"],
    }
    return summary, items


def analyze_pool(characters: list[dict], pool_name: str) -> dict:
    pool_score = _mock_pool_score(characters)
    recommendation = _mock_recommendation(pool_score)
    explanation_summary, explanation_items = _build_explanation_items(characters)

    if not explanation_items:
        explanation_items = [
            {
                "head": "此卡池",
                "points": ["尚無可條列的角色資料"],
                "id": "",
            }
        ]

    visible_count = 5
    return {
        "pool_score": pool_score,
        "pool_score_label": f"{pool_score} / 100",
        "is_mock_score": True,
        "recommendation": recommendation,
        "explanation_summary": explanation_summary,
        "explanation_items": explanation_items,
        "explanation_visible": explanation_items[:visible_count],
        "explanation_hidden": explanation_items[visible_count:],
        "explanation_has_more": len(explanation_items) > visible_count,
        "explanation_hidden_count": max(0, len(explanation_items) - visible_count),
    }
