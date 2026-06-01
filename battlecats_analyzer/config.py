import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Render / 本機請設環境變數 SESSION_SECRET；未設則每次重啟會重置 session（開發用）
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)
SESSION_COOKIE_NAME = "battlecats_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 天
SESSION_KEY_OWNED = "owned_cat_ids"

DATA_JSON = ROOT / "DA_ML_期末專案" / "爬蟲" / "rated_data" / "battlecats_ALL_db.json"
GACHA_JSON = ROOT / "BattleCats_Output" / "gacha_id_list.json"
ML_DIR = ROOT / "battle_cats_ml_test3"
CHARACTERS_JSON = Path(__file__).resolve().parent / "data" / "characters.json"
MODULE_SCORES_CSV = Path(__file__).resolve().parent / "data" / "module_scores_export.csv"

APP_TITLE = "Battle Cats Analyzer"
POOL_NAME = "超極貓祭"
PHONE_MAX_WIDTH = 390

def unit_image_url(cat_id: str, *, local: bool = True) -> str:
    """Official sprites live on battlecats-db.imgs-server.com (not /img/unit_icon/)."""
    cid = str(cat_id).zfill(3)
    if local:
        return f"/image/{cid}"
    return f"https://battlecats-db.imgs-server.com/u{cid}-1.png"
