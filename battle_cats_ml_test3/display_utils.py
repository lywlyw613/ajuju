from game_labels import ENEMY_TRAIT_CN, ABILITY_NAME_CN

def trait_index_to_cn(i: int) -> str:
    if 0 <= i < len(ENEMY_TRAIT_CN):
        return ENEMY_TRAIT_CN[i]
    return f"索引{i}"

def ability_id_to_cn(aid: int) -> str:
    return ABILITY_NAME_CN.get(int(aid), f"未知能力{aid}")

def format_active_enemies(flags: list[bool] | None) -> str:
    if not flags:
        return ""
    return ", ".join(trait_index_to_cn(i) for i, on in enumerate(flags) if on)

def list_active_abilities(ability_dict: dict) -> str:
    lines = []
    for ab in ability_dict.values():
        if not ab.get("有此能力"):
            continue
        aid = int(ab.get("能力ID", 0))
        targets = format_active_enemies(ab.get("生效敵人", []))
        name = ability_id_to_cn(aid)
        prob = ab.get("機率", 0)
        if targets:
            lines.append(f"ID{aid} {name} → {targets} (機率{prob}%)")
        else:
            lines.append(f"ID{aid} {name} (機率{prob}%)")
    return "; ".join(lines) if lines else "（無）"
