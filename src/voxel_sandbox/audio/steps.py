from __future__ import annotations

from collections.abc import Container


def footstep_sound_key(material: str, available_sounds: Container[str]) -> str:
    material_key = f"step.{material}"
    if material_key in available_sounds:
        return material_key
    return "footstep"
