from __future__ import annotations 

import numpy as np
import pandas as pd

from data_io import pick_form
from display_utils import list_active_abilities
from game_labels import (
    ALWAYS_ACTIVE_IDS,
    ENEMY_TRAIT_CN,
    IGNORED_ABILITY_IDS,
    MODULE_1_ABILITY_IDS,
    MODULE_2_ABILITY_IDS,
    MODULE_3_ABILITY_IDS,
    SCORED_IDS,
)

def _safe_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def sum_abilities_mod1(ability_dict: dict) -> float:
    total = 0.0
    for ab in ability_dict.values():
        aid = int(ab.get("能力ID", 0))
        if aid in IGNORED_ABILITY_IDS:
            continue
        if aid in MODULE_1_ABILITY_IDS:
            total += ability_contrib(ab)
    return total


def sum_abilities_by_trait(ability_dict: dict, module_ids: set) -> list[float]:
    scores = [0.0] * 15
    for ab in ability_dict.values():
        aid = int(ab.get("能力ID", 0))
        if aid not in module_ids or not ab.get("有此能力"):
            continue
        flags = ab.get("生效敵人", [])
        for t in range(min(15, len(flags))):
            if flags[t]:
                scores[t] += ability_contrib(ab)
    return scores


def control_global_contrib(ability_dict: dict) -> float:
    total = 0.0
    for ab in ability_dict.values():
        aid = int(ab.get("能力ID", 0))
        if aid not in MODULE_3_ABILITY_IDS or not ab.get("有此能力"):
            continue
        flags = ab.get("生效敵人", [])
        if flags and any(flags):
            continue
        total += ability_contrib(ab)
    return total


def _trait_names_from_scores(scores: list[float]) -> str:
    names = []
    for i, v in enumerate(scores):
        if i < len(ENEMY_TRAIT_CN) and float(v) > 0:
            names.append(ENEMY_TRAIT_CN[i])
    return "、".join(names) if names else "無"

def _merge_trait_names(trait_mod2_cn: str, trait_mod3_cn: str) -> str:
    """合併模組2/3針對屬性，去重後只顯示一次。"""
    names = []
    for part in (trait_mod2_cn, trait_mod3_cn):
        if not part or part == "無":
            continue
        for name in part.split("、"):
            name = name.strip()
            if name and name not in names:
                names.append(name)
    return "、".join(names) if names else "無"
    
def ability_contrib(ab: dict) -> float:
    if not ab.get("有此能力"):
        return 0.0
    aid = int(ab.get("能力ID", 0))
    if aid not in SCORED_IDS:
        return 0.0
    s = max(float(ab.get("效果強度", 0)), 0.01) # 效果強度已包含
    if ab.get("效果長度", 0) > 0:
        s *= 1 + ab["效果長度"] / 100.0 # 效果長度（持續時間）已包含
    prob = 1.0 if aid in ALWAYS_ACTIVE_IDS else ab.get("機率", 0) / 100.0 # 機率已包含
    return prob * s

def extract_panel(form: dict) -> dict[str, float]:
    cost = max(_safe_float(form.get("成本"), 1), 1)
    dps = _safe_float(form.get("DPS"))
    hp = _safe_float(form.get("體力"))
    return {
        "體力": hp,
        "DPS": dps,
        "射程": _safe_float(form.get("射程")),
        "速度": _safe_float(form.get("速度")),
        "攻擊頻率": _safe_float(form.get("攻擊頻率")),
        "成本": _safe_float(form.get("成本")),
        "dps_per_cost": dps / cost,
        "hp_per_cost": hp / cost,
    }

def char_to_row(char_key: str, char: dict) -> dict | None:
    stage, form = pick_form(char)
    if not form:
        return None
    panel = extract_panel(form)
    abilities = form.get("能力", {})
    trait_scores = sum_abilities_by_trait(abilities, MODULE_2_ABILITY_IDS)
    control_scores = sum_abilities_by_trait(abilities, MODULE_3_ABILITY_IDS)
    ctrl_global = control_global_contrib(abilities)

    label = char.get("評分", char.get("排名"))
    if label in (None, "", "NAN", "nan"):
        label = np.nan
    else:
        try:
            label = max(0.0, min(4.5, float(label)))
        except (TypeError, ValueError):
            label = np.nan

    trait_max = max(trait_scores) if trait_scores else 0.0
    control_max = max(control_scores) if control_scores else 0.0
    mod1_ability = sum_abilities_mod1(abilities)
    trait_mod2_cn = _trait_names_from_scores(trait_scores)
    trait_mod3_cn = _trait_names_from_scores(control_scores)

    row = {
        "角色鍵": char_key,
        "名字": form.get("名字"),
        "form_stage": stage,
        "評分": label,
        "啟用能力_中文": list_active_abilities(abilities),
        "mod1_ability_raw": mod1_ability,
        "mod2_raw": trait_max,
        "mod3_raw": control_max + 0.5 * ctrl_global,
        "trait_raw_max": trait_max,
        "control_raw_max": control_max,
        "control_global_raw": ctrl_global,
        "模組2針對屬性": trait_mod2_cn,
        "模組3針對屬性": trait_mod3_cn,
        "針對屬性": _merge_trait_names(trait_mod2_cn, trait_mod3_cn),
        **panel,
    }
    for i, v in enumerate(trait_scores):
        row[f"trait_raw_{i}"] = v
    for i, v in enumerate(control_scores):
        row[f"control_raw_{i}"] = v
    return row

def raw_to_rows(raw: dict | list) -> list[dict]:
    rows = []
    if isinstance(raw, dict):
        items = raw.items()
    elif isinstance(raw, list):
        items = [(str(i), c) for i, c in enumerate(raw)]
    else:
        raise TypeError(f"不支援的 JSON 型別: {type(raw)}")
    for key, char in items:
        if not isinstance(char, dict):
            continue
        r = char_to_row(str(key), char)
        if r:
            rows.append(r)
    return rows

def build_feature_dataframe(raw):
    from scoring import add_module_scores

    df = pd.DataFrame(raw_to_rows(raw))
    if df.empty:
        return df
    return add_module_scores(df)
