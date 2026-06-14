from __future__ import annotations

from pathlib import Path

from voxel_sandbox.engine.generation import load_structure_templates


def run_preview(template_key: str) -> int:
    root = Path(__file__).parents[1] / "engine/generation/structure_templates"
    templates = {template.key: template for template in load_structure_templates(root)}
    template = templates.get(template_key)
    if template is None:
        available = ", ".join(sorted(templates))
        raise ValueError(f"Unknown structure {template_key!r}; available: {available}")
    occupied = {(block.x, block.y, block.z): block.block_id for block in template.blocks}
    print(f"{template.key} size={template.size} rarity={template.rarity}")
    for y in range(template.size[1] - 1, -1, -1):
        if not any(position[1] == y for position in occupied):
            continue
        print(f"layer y={y}")
        for z in range(template.size[2]):
            print(" ".join(f"{occupied.get((x, y, z), 0):02d}" for x in range(template.size[0])))
    if template.loot:
        print(
            "loot "
            + ", ".join(
                f"item={entry.item_id} count={entry.minimum}-{entry.maximum} weight={entry.weight}"
                for entry in template.loot
            )
        )
    return 0
