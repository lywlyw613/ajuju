# scoring.py — 模組1/2/3 各自 0~10 分（各軌獨立 min-max）

from __future__ import annotations

import pandas as pd


MODULE1_PANEL_WEIGHTS = {
    "dps_per_cost": 0.35,
    "DPS": 0.25,
    "射程": 0.15,
    "速度": 0.10,
    "攻擊頻率": 0.10,
    "成本": -0.05,
}


def normalize_minmax(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi <= lo:
        return pd.Series(0.5, index=series.index)
    return (series - lo) / (hi - lo)


def scale_to_0_10(norm: pd.Series, target_max_score: float = 9.5, power_factor: float = 0.8) -> pd.Series:
    clipped_norm = norm.clip(0, 1)
    # 診斷用途：打印 norm 的統計信息
    print(f"DEBUG: norm.describe() before power_factor:\n{clipped_norm.describe()}")
    print(f"DEBUG: norm.max() before power_factor: {clipped_norm.max()}")
    print(f"DEBUG: norm.median() before power_factor: {clipped_norm.median()}")
    boosted_norm = clipped_norm ** power_factor
    # 診斷用途：打印 boosted_norm 的統計信息
    print(f"DEBUG: boosted_norm.describe() after power_factor:\n{boosted_norm.describe()}")
    print(f"DEBUG: boosted_norm.max() after power_factor: {boosted_norm.max()}")
    return (boosted_norm * target_max_score).astype(float)


def compute_module1_panel_raw(df: pd.DataFrame) -> pd.Series:
    """模組1：僅面板（DPS、成本效率等）。"""
    parts = []
    for col, w in MODULE1_PANEL_WEIGHTS.items():
        if col not in df.columns:
            continue
        parts.append(w * normalize_minmax(df[col].astype(float)))
    if not parts:
        return pd.Series(0.0, index=df.index)
    return sum(parts)


def compute_module1_raw(df: pd.DataFrame) -> pd.Series:
    """模組1：面板 + mod1_ability_raw。"""
    ability = df["mod1_ability_raw"].astype(float) if "mod1_ability_raw" in df.columns else 0.0
    return compute_module1_panel_raw(df) + ability


# scoring.py
# ...
MODULE2_TRAIT_WEIGHTS = { # 您之前已添加
    "trait_raw_0": 1.0,  # "無屬性"
    "trait_raw_1": 1.0,  # "紅色敵人"
    "trait_raw_2": 1.0,  # "黑色敵人"
    "trait_raw_3": 1.0,  # "漂浮敵人"
    "trait_raw_4": 1.0,  # "鋼鐵敵人"
    "trait_raw_5": 1.0,  # "天使"
    "trait_raw_6": 1.0,  # "異星敵人"
    "trait_raw_7": 1.0,  # "不死敵人"
    "trait_raw_8": 1.0,  # "古代種"
    "trait_raw_9": 1.0,  # "惡魔"
    "trait_raw_10": 1.0, # "超生命體"
    "trait_raw_11": 1.0, # "超獸"
    "trait_raw_12": 1.0, # "超賢者"
    "trait_raw_13": 1.0, # "魔女"
    "trait_raw_14": 1.0, # "使徒"
}

# 定義模組2的屬性加成
MODULE2_BONUS_TRAITS = {
    "trait_raw_0": 0.5,
    "trait_raw_8": 0.5,
    "trait_raw_9": 0.5,
}

def compute_module2_raw(df: pd.DataFrame) -> pd.Series:
    """模組2：對屬性 ab1-5 倍率+屬性權重，並針對特定屬性加成。"""
    parts = []
    for col, w in MODULE2_TRAIT_WEIGHTS.items():
        if col in df.columns:
            parts.append(w * df[col].astype(float))

    # 新增屬性加成
    for trait_col, bonus_val in MODULE2_BONUS_TRAITS.items():
        if trait_col in df.columns:
            # 只有當該屬性有作用時才加成 (即 trait_raw_X > 0)
            parts.append(df[trait_col].apply(lambda x: bonus_val if x > 0 else 0.0))

    if not parts:
        return pd.Series(0.0, index=df.index)
    return sum(parts)


MODULE3_BONUS_TRAITS = {
    "trait_raw_0": 0.5,
    "trait_raw_4": 0.8,
    "trait_raw_8": 0.5,
    "trait_raw_9": 0.5,
}
def compute_module3_raw(df: pd.DataFrame) -> pd.Series:
    """模組3：計算控場覆蓋率 (control coverage rate)，並針對特定屬性加成。"""
    control_cols = [f"control_raw_{i}" for i in range(15)]
    control_max_effect = df[control_cols].fillna(0).max(axis=1)
    global_control_effect = df["control_global_raw"].fillna(0)
    # 基礎分數
    base_score = control_max_effect + 0.5 * global_control_effect
    # 屬性加成
    bonus_score = pd.Series(0.0, index=df.index)
    for trait_col, bonus_val in MODULE3_BONUS_TRAITS.items():
        if trait_col in df.columns:
            # 只有當該屬性有作用時才加成 (即 trait_raw_X > 0)
            bonus_score += df[trait_col].apply(lambda x: bonus_val if x > 0 else 0.0)
    return base_score + bonus_score


def add_module_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["mod1_panel_raw"] = compute_module1_panel_raw(out)
    out["mod1_raw"] = compute_module1_raw(out)
    out["mod2_raw"] = compute_module2_raw(out)
    out["mod3_raw"] = compute_module3_raw(out)

    out["score_mod1"] = scale_to_0_10(normalize_minmax(out["mod1_raw"]))
    out["score_mod2"] = scale_to_0_10(normalize_minmax(out["mod2_raw"]))
    out["score_mod3"] = scale_to_0_10(normalize_minmax(out["mod3_raw"]))
    return out