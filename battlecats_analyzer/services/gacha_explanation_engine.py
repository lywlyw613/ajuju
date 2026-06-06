"""Explainable gacha pool recommendation engine (from DA_ML_PoolScore notebook).

Inputs:
  pool_name  — Japanese gacha key in gacha_pool_characters_mapping.json
  owned_ids  — list of owned character IDs, e.g. ["045", "706"]

Outputs:
  ev_current, recommendation_level, stats, pockets, display_explanations
"""

from __future__ import annotations

from services.gacha_pools import load_gacha_pools
from services.tier_list import load_tier_list

PR40_THRESHOLD = 0.1185
PR80_THRESHOLD = 0.1366

GOD_TIER_LIMIT = 4.3
S_TIER_LIMIT = 3.75
A_TIER_LIMIT = 3.25

P_SSR = 0.05
P_SSSR = 0.003

DEFAULT_SCORE = 2.5
DEFAULT_SCORE_BATCH = 2.37


def _recommendation_for_ev(ev: float) -> str:
    if ev >= PR80_THRESHOLD:
        return "🔥 極度推薦 (必抽神池)"
    if ev >= PR40_THRESHOLD:
        return "👍 推薦抽取 (性價比高)"
    return "❌ 可跳過 (當前價值低)"


def _recommendation_for_ev_batch(ev: float) -> str:
    if ev >= PR80_THRESHOLD:
        return "🔥 極度推薦 (PR80以上神池)"
    if ev >= PR40_THRESHOLD:
        return "👍 推薦抽取 (PR40以上好池)"
    return "❌ 可跳過 (當前價值過低)"


def _skip_reason_label(skip_type: str) -> str:
    return {
        "none": "—",
        "high_duplication": "重複過高（好池但對您價值低）",
        "low_quality": "本質弱池（baseline 即低於 PR40）",
    }.get(skip_type, skip_type)


def _pocket_tier(score: float, is_owned: bool) -> str:
    if is_owned:
        return "owned"
    if score >= GOD_TIER_LIMIT:
        return "god"
    if score >= S_TIER_LIMIT:
        return "s"
    if score >= A_TIER_LIMIT:
        return "a"
    return "trap"


def rank_all_pools(owned_ids: list[str] | None = None) -> dict:
    """Batch ranking like notebook Cell 0 `gacha_recommendation_system_pr`."""
    owned_ids = owned_ids or []
    tier = load_tier_list()
    pool_mapping = load_gacha_pools()
    owned_set = {str(cat_id).zfill(3) for cat_id in owned_ids}

    rows: list[dict] = []
    for pool_name, rarities in pool_mapping.items():
        ssr_list = rarities.get("SSR", [])
        sssr_list = rarities.get("SSSR", [])
        n_ssr = len(ssr_list)
        n_sssr = len(sssr_list)
        if n_ssr == 0 and n_sssr == 0:
            continue

        p_ssr = P_SSR / n_ssr if n_ssr > 0 else 0.0
        p_sssr = P_SSSR / n_sssr if n_sssr > 0 else 0.0
        ev_current = 0.0
        ev_initial = 0.0
        owned_ssr = 0
        owned_sssr = 0

        for cat_id in ssr_list:
            row = tier.get(cat_id)
            score = float(row["composite_score"]) if row and row.get("composite_score") is not None else DEFAULT_SCORE_BATCH
            ev_initial += p_ssr * score
            if cat_id in owned_set:
                owned_ssr += 1
            else:
                ev_current += p_ssr * score

        for cat_id in sssr_list:
            row = tier.get(cat_id)
            score = float(row["composite_score"]) if row and row.get("composite_score") is not None else DEFAULT_SCORE_BATCH
            ev_initial += p_sssr * score
            if cat_id in owned_set:
                owned_sssr += 1
            else:
                ev_current += p_sssr * score

        rows.append(
            {
                "pool_name": pool_name,
                "ev_current": round(ev_current, 4),
                "ev_initial": round(ev_initial, 4),
                "total_ssr": n_ssr,
                "owned_ssr": owned_ssr,
                "total_sssr": n_sssr,
                "owned_sssr": owned_sssr,
                "recommendation_level": _recommendation_for_ev_batch(ev_current),
            }
        )

    rows.sort(key=lambda r: (-r["ev_current"], r["pool_name"]))
    for i, row in enumerate(rows, start=1):
        row["rank"] = i

    return {
        "thresholds": {
            "pr40": PR40_THRESHOLD,
            "pr80": PR80_THRESHOLD,
        },
        "total_pools": len(rows),
        "rows": rows,
    }


def _char_score_and_name(cat_id: str, tier: dict[str, dict]) -> tuple[float, str]:
    row = tier.get(cat_id)
    if not row:
        return DEFAULT_SCORE, "未知角色"
    score = row.get("composite_score")
    if score is None:
        score = DEFAULT_SCORE
    name = row.get("name") or "未知角色"
    return float(score), name


def calculate_gacha_explanation_engine(pool_name: str, owned_ids: list[str] | None = None) -> dict:
    owned_ids = owned_ids or []
    tier = load_tier_list()
    pool_mapping = load_gacha_pools()

    if pool_name not in pool_mapping:
        return {"status": "error", "message": "找不到指定的卡池", "pool_name": pool_name}

    ssr_list = pool_mapping[pool_name].get("SSR", [])
    sssr_list = pool_mapping[pool_name].get("SSSR", [])
    n_ssr = len(ssr_list)
    n_sssr = len(sssr_list)
    total_pool_chars = n_ssr + n_sssr

    if total_pool_chars == 0:
        return {"status": "error", "message": "此卡池內無超激或傳說稀有角色", "pool_name": pool_name}

    p_ssr = P_SSR / n_ssr if n_ssr > 0 else 0.0
    p_sssr = P_SSSR / n_sssr if n_sssr > 0 else 0.0
    owned_set = {str(cat_id).zfill(3) for cat_id in owned_ids}

    god_unowned_pocket: list[dict] = []
    s_unowned_pocket: list[dict] = []
    a_unowned_pocket: list[dict] = []
    owned_or_trap_pocket: list[dict] = []
    character_roster: list[dict] = []

    ev_initial = 0.0
    ev_current = 0.0
    owned_ssr_count = 0
    owned_sssr_count = 0
    trap_count = 0

    all_pool_chars = [(cat_id, "SSR", p_ssr) for cat_id in ssr_list]
    if sssr_list:
        all_pool_chars += [(cat_id, "SSSR", p_sssr) for cat_id in sssr_list]

    for cat_id, rarity, p_weight in all_pool_chars:
        score, name = _char_score_and_name(cat_id, tier)
        is_owned = cat_id in owned_set
        ev_init_contrib = round(p_weight * score, 6)
        ev_curr_contrib = 0.0 if is_owned else ev_init_contrib
        tier_key = _pocket_tier(score, is_owned)

        char_info = {
            "id": cat_id,
            "name": name,
            "rarity": rarity,
            "score": round(score, 2),
            "owned": is_owned,
            "p_weight": round(p_weight, 6),
            "p_weight_pct": f"{p_weight * 100:.4f}%",
            "ev_initial_contrib": ev_init_contrib,
            "ev_current_contrib": ev_curr_contrib,
            "pocket_tier": tier_key,
        }
        character_roster.append(char_info)

        ev_initial += p_weight * score

        if is_owned:
            if rarity == "SSR":
                owned_ssr_count += 1
            else:
                owned_sssr_count += 1
            owned_or_trap_pocket.append(char_info)
            continue

        if score >= GOD_TIER_LIMIT:
            god_unowned_pocket.append(char_info)
            ev_current += p_weight * score
        elif score >= S_TIER_LIMIT:
            s_unowned_pocket.append(char_info)
            ev_current += p_weight * score
        elif score >= A_TIER_LIMIT:
            a_unowned_pocket.append(char_info)
            ev_current += p_weight * score
        else:
            trap_count += 1
            owned_or_trap_pocket.append(char_info)
            ev_current += p_weight * score

    recommendation_level = _recommendation_for_ev(ev_current)

    explanations = {"core_reason": "", "sub_reason": "", "risk_hint": ""}
    dup_rate_percent = f"{round(((owned_ssr_count + owned_sssr_count) / total_pool_chars) * 100, 1)}%"

    if recommendation_level == "🔥 極度推薦 (必抽神池)":
        if god_unowned_pocket:
            god_names = "、".join([f"「{c['name']}」" for c in god_unowned_pocket])
            explanations["core_reason"] = (
                f"🎯 此卡池包含目前遊戲環境中最強大的主宰級神貓，且您尚未擁有：{god_names}！"
                f"牠們的強度均超越 {GOD_TIER_LIMIT} 分，是絕對值得您耗費資源全力狙擊的核心目標！"
            )
        else:
            explanations["core_reason"] = (
                f"⚔️ 雖然目前池中沒有高於 {GOD_TIER_LIMIT} 的極限神貓（或您已擁有），"
                "但該池的綜合期望值表現傲視群雄，對您而言仍具有統治級的抽取價值。"
            )

        if s_unowned_pocket:
            s_names = "、".join([f"「{c['name']}」" for c in s_unowned_pocket[:3]])
            suffix = "等車輪戰力" if len(s_unowned_pocket) > 3 else "等頂級戰力"
            explanations["sub_reason"] = (
                f"🛡️ 頂級戰力補充：除了核心目標，池內還躺著您未擁有的一線強勢角色：{s_names}{suffix}，"
                "能瞬間極大化您的隊伍深度，抽到任何一隻都是大賺！"
            )

        if a_unowned_pocket:
            explanations["risk_hint"] = (
                f"📋 優質副產物提示：清單中亦有多達 {len(a_unowned_pocket)} 隻 A 級中流砥柱角色等待開榜，"
                "整體雜魚率極低，是一次高勝率的投資。"
            )

    elif recommendation_level == "👍 推薦抽取 (性價比高)":
        total_good_unowned = len(s_unowned_pocket) + len(a_unowned_pocket)
        explanations["core_reason"] = (
            f"⚖️ 穩健投資首選：該卡池整體的綜合品質非常優良。雖然缺乏一隻定乾坤的超級神仙（或您已擁有），"
            f"但您尚未擁有的頂級與優質角色高達 {total_good_unowned} 隻。"
            "整體池子深厚，能為您提供非常穩健的下限回報。"
        )

        if s_unowned_pocket:
            s_names = "、".join([f"「{c['name']}」" for c in s_unowned_pocket])
            explanations["sub_reason"] = (
                f"💪 推薦瞄準目標：建議將目標放在尚未擁有的強勢一線角色：{s_names}，"
                "這將是提升戰力的最佳跳板。"
            )

        explanations["risk_hint"] = (
            f"⚠️ 抽卡風險評估：目前您在此池的重複率為 {dup_rate_percent}，仍處於安全投資水位。"
            f"但請注意池內仍有 {trap_count} 隻環境弱勢的倉管角色，請適度控制投入的罐頭與金券。"
        )

    elif recommendation_level == "❌ 可跳過 (當前價值低)":
        if skip_reason_type == "high_duplication":
            explanations["core_reason"] = (
                f"🛑 重複陷阱警告：此卡池本質非常優秀，但對「目前的您」而言是一座高風險的重複大墳墓！"
                f"由於您已經開拓了此池最核心的戰力（重複率達 {dup_rate_percent}），"
                "強烈建議保持克制，不要把寶貴的資源花在重複率極高的池子裡。"
            )
            explanations["sub_reason"] = "💡 建議：將罐頭與金券留給其他完全未開發的新卡池，本池直接規劃退場。"
        else:
            trap_ratio = f"{round((trap_count / total_pool_chars) * 100, 1)}%"
            explanations["core_reason"] = (
                f"🗑️ 避雷勸退指南：此卡池在目前的遊戲 Meta 環境中表現普遍低迷。"
                f"池內缺乏具備決定性的強勢核心，且充斥著高達 {trap_ratio} 的弱勢倉管角色。"
                "無論您是否擁有這裏的角色，投資報酬率都非常低迷。"
            )
            explanations["sub_reason"] = (
                "💡 建議：此卡池純屬時代眼淚或地雷卡池，建議完全無視，儲存資源等候超極貓祭等大活動。"
            )

    skip_reason_type = "none"
    if recommendation_level.startswith("❌"):
        if ev_initial >= PR40_THRESHOLD:
            skip_reason_type = "high_duplication"
        else:
            skip_reason_type = "low_quality"

    ssr_roster = [c for c in character_roster if c["rarity"] == "SSR"]
    sssr_roster = [c for c in character_roster if c["rarity"] == "SSSR"]

    return {
        "status": "success",
        "pool_name": pool_name,
        "metrics": {
            "ev_initial": round(ev_initial, 4),
            "ev_current": round(ev_current, 4),
            "recommendation_level": recommendation_level,
            "skip_reason_type": skip_reason_type,
            "skip_reason_label": _skip_reason_label(skip_reason_type),
            "thresholds": {
                "pr40": PR40_THRESHOLD,
                "pr80": PR80_THRESHOLD,
                "p_ssr": round(p_ssr, 6),
                "p_sssr": round(p_sssr, 6),
                "p_ssr_pct": f"{P_SSR * 100}%",
                "p_sssr_pct": f"{P_SSSR * 100}%",
            },
            "stats": {
                "total_ssr": n_ssr,
                "owned_ssr": owned_ssr_count,
                "total_sssr": n_sssr,
                "owned_sssr": owned_sssr_count,
                "dup_rate": dup_rate_percent,
                "trap_count": trap_count,
                "total_chars": total_pool_chars,
            },
        },
        "pockets": {
            "god_unowned": god_unowned_pocket,
            "s_unowned": s_unowned_pocket,
            "a_unowned": a_unowned_pocket,
            "owned_or_trap": owned_or_trap_pocket,
            "owned_or_trap_count": len(owned_or_trap_pocket),
        },
        "character_roster": character_roster,
        "ssr_roster": ssr_roster,
        "sssr_roster": sssr_roster,
        "display_explanations": explanations,
    }
