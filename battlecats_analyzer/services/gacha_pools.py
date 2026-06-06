"""Load gacha_pool_characters_mapping.json — pool name to SSR/SSSR ID lists."""

from __future__ import annotations

import json
from pathlib import Path

from config import DEFAULT_POOL_KEY, GACHA_POOLS_JSON

_pools: dict | None = None


def load_gacha_pools() -> dict[str, dict[str, list[str]]]:
    global _pools
    if _pools is not None:
        return _pools

    if not GACHA_POOLS_JSON.is_file():
        _pools = {}
        return _pools

    with open(GACHA_POOLS_JSON, encoding="utf-8") as f:
        raw = json.load(f)

    out: dict[str, dict[str, list[str]]] = {}
    for pool_name, tiers in raw.items():
        if not isinstance(tiers, dict):
            continue
        out[pool_name] = {
            "SSR": [str(i).zfill(3) for i in tiers.get("SSR", [])],
            "SSSR": [str(i).zfill(3) for i in tiers.get("SSSR", [])],
        }

    _pools = out
    return out


def list_pool_names() -> list[str]:
    return sorted(load_gacha_pools().keys())


def resolve_pool_key(name: str | None) -> str | None:
    pools = load_gacha_pools()
    if not pools:
        return None
    if name and name in pools:
        return name
    if DEFAULT_POOL_KEY in pools:
        return DEFAULT_POOL_KEY
    return next(iter(pools))


def get_pool_ids(pool_key: str) -> list[tuple[str, str]]:
    """Return [(cat_id, rarity), ...] for SSR and SSSR in pool."""
    pools = load_gacha_pools()
    entry = pools.get(pool_key, {})
    items: list[tuple[str, str]] = []
    for rarity in ("SSSR", "SSR"):
        for cid in entry.get(rarity, []):
            items.append((str(cid).zfill(3), rarity))
    return items


def pools_with_ssr() -> list[str]:
    """Pools that have at least one SSR or SSSR character."""
    result = []
    for name, tiers in load_gacha_pools().items():
        if tiers.get("SSR") or tiers.get("SSSR"):
            result.append(name)
    return sorted(result)
