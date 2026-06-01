"""Rule-based AI commentary from character stats and abilities."""

from __future__ import annotations


def _num(val, default: float = 0.0) -> float:
    try:
        if val in (None, "", "NAN", "nan"):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def build_ai_analysis(char: dict, form: dict, row: dict | None = None) -> dict:
    """Return pull reasons, pros, cons for detail / gacha pages."""
    reasons: list[str] = []
    pros: list[str] = []
    cons: list[str] = []

    dps = _num(form.get("DPS"))
    hp = _num(form.get("體力"))
    cost = max(_num(form.get("成本"), 1), 1)
    dps_per_cost = dps / cost if cost else 0
    trait = (row or {}).get("針對屬性", "") or ""
    score_mod1 = _num((row or {}).get("score_mod1"))
    score_mod2 = _num((row or {}).get("score_mod2"))
    score_mod3 = _num((row or {}).get("score_mod3"))
    rating = char.get("評分")
    if rating not in (None, "", "NAN", "nan"):
        try:
            r = float(rating)
            if r >= 3.5:
                reasons.append("社群評價偏高，整體評分優秀")
            elif r >= 2.5:
                reasons.append("評價穩定，具一定抽取價值")
        except (TypeError, ValueError):
            pass

    if dps_per_cost >= 8:
        reasons.append("泛用性高")
        pros.append("成本效益佳（DPS/成本表現突出）")
    elif dps_per_cost >= 4:
        pros.append("輸出與成本平衡尚可")

    if dps >= 15000:
        pros.append("DPS 極高")
    elif dps >= 8000:
        pros.append("爆發輸出強")

    if hp >= 80000:
        pros.append("體力厚、站場能力佳")

    if "黑" in trait:
        reasons.append("對黑敵優秀")
        pros.append("針對黑色敵人效果好")
    if "紅" in trait:
        pros.append("對紅敵有優勢")
    if "浮" in trait:
        pros.append("對浮敵有優勢")

    if score_mod2 >= 7:
        reasons.append("屬性特攻模組表現強")
    if score_mod3 >= 7:
        reasons.append("控場模組表現強")

    if cost >= 5000:
        cons.append("成本偏高")
    repro = _num(form.get("再生產"))
    if repro >= 120:
        cons.append("生產速度較慢")

    atk_freq = _num(form.get("攻擊頻率"))
    if atk_freq >= 90:
        cons.append("攻擊間隔較長")

    if not reasons:
        reasons.append("可作為卡池補強角色參考")
    if not pros:
        pros.append("具備基本實戰數值，可視隊伍需求抽取")
    if not cons:
        cons.append("建議搭配陣容與關卡類型評估")

    reasons.append("中後期仍有價值")

    return {
        "reasons": reasons[:5],
        "pros": pros[:5],
        "cons": cons[:5],
    }
