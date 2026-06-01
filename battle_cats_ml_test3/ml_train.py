from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

# 不當特徵的欄位
ID_COLS = [
    "角色鍵", "名字", "form_stage",
    "啟用能力_中文", "trait_best_enemy", "control_best_enemy",
]
TARGET_COL = "評分"


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    exclude = set(ID_COLS + [TARGET_COL])
    return [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]


def rating_to_score_10(rating: float) -> float:
    """0–4.5 標籤 → 0–10 顯示分；0 略抬、4.5 壓到約 9。"""
    if pd.isna(rating):
        return np.nan
    r = float(np.clip(rating, 0.0, 4.5))
    # 線性映射到 [1, 9]，保留 0–10 空間的兩端
    return float(1.0 + (r / 4.5) * 8.0)


def prepare_xy(df: pd.DataFrame, feature_cols: list[str] | None = None):
    labeled = df[df[TARGET_COL].notna()].copy()
    if feature_cols is None:
        feature_cols = get_feature_columns(labeled)
    X = labeled[feature_cols].fillna(0)
    y = labeled[TARGET_COL].astype(float)
    return X, y, feature_cols, labeled.index


def train_model(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
):
    X, y, feature_cols, _ = prepare_xy(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    pred_test = model.predict(X_test)
    sp, _ = spearmanr(y_test, pred_test)
    mae = mean_absolute_error(y_test, pred_test)
    metrics = {
        "n_train": len(X_train),
        "n_test": len(X_test),
        "spearman": float(sp) if not np.isnan(sp) else None,
        "mae": float(mae),
        "feature_cols": feature_cols,
    }
    return model, metrics


def predict_dataframe(df: pd.DataFrame, model, feature_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    X_all = out[feature_cols].fillna(0)
    out["pred_評分"] = model.predict(X_all).clip(0, 4.5)
    out["score_10"] = out["pred_評分"].map(rating_to_score_10)
    if TARGET_COL in out.columns:
        out["score_10_label"] = out[TARGET_COL].map(rating_to_score_10)
    return out