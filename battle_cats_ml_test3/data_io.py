import json
from pathlib import Path

FORM_PRIORITY = [
    "四階滿本能",
    "四階資料",
    "三階滿本能",
    "三階資料",
    "二階資料",
]

def pick_form(char: dict) -> tuple[str | None, dict | None]:
    for key in FORM_PRIORITY:
        v = char.get(key)
        if v not in (None, "NAN", "nan", ""):
            if isinstance(v, dict):
                return key, v
    return None, None

def load_raw(path: str | Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)