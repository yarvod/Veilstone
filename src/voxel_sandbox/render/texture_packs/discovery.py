from __future__ import annotations

from pathlib import Path

from voxel_sandbox.render.texture_packs.minecraft_java import is_minecraft_java_pack


def discover_texture_packs(root: Path) -> list[tuple[str, Path | None]]:
    packs: list[tuple[str, Path | None]] = []
    if not root.exists():
        return packs

    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if path.name.startswith(".") or path.name == "README.md":
            continue
        if (path.is_dir() or path.suffix.lower() == ".zip") and is_minecraft_java_pack(path):
            packs.append((path.name, path))
    return packs
