"""Pool-level analysis: Pool Score, Recommendation, Explanation.

Pool Score and Recommendation use mock formulas until backend models are ready.
Explanation pulls from id_review_sections_export.csv for top characters in pool.
"""

from __future__ import annotations

from services.review_sections import build_explanation_snippet, get_review


def _mock_pool_score(characters: list[dict]) -> float:
    """0–100 mock score from average composite tier score (0–5)."""
    scores = [c["tier"]["composite_score"] for c in characters if c.get("tier") and c["tier"].get("composite_score") is not None]
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


def analyze_pool(characters: list[dict], pool_name: str) -> dict:
    pool_score = _mock_pool_score(characters)
    recommendation = _mock_recommendation(pool_score)

    ranked = sorted(
        characters,
        key=lambda c: (c.get("tier") or {}).get("composite_score") or 0,
        reverse=True,
    )

    explanation_lines: list[str] = [f"卡池「{pool_name}」分析摘要（Explanation 引用角色評語資料）：", ""]
    top = [c for c in ranked if get_review(c["id"])][:3]

    if top:
        explanation_lines.append("推薦抽取 — 原因：")
        explanation_lines.append("")
        for c in top:
            review = get_review(c["id"])
            name = c.get("name") or (review or {}).get("name", c["id"])
            explanation_lines.append(f"◆ {name}")
            for line in build_explanation_snippet(review, name):
                explanation_lines.append(f"  · {line}")
            explanation_lines.append("")
    else:
        explanation_lines.append("此卡池尚無可引用的角色評語資料。")

    s_count = sum(1 for c in characters if (c.get("tier") or {}).get("composite_grade") == "S")
    explanation_lines.append(
        f"（統計）共 {len(characters)} 隻 SSR/SSSR，其中 S 等第 {s_count} 隻。"
    )

    return {
        "pool_score": pool_score,
        "pool_score_label": f"{pool_score} / 100",
        "is_mock_score": True,
        "recommendation": recommendation,
        "explanation": "\n".join(explanation_lines).strip(),
    }
