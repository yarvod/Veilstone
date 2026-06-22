from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from voxel_sandbox.domain.blocks import BlockRegistry, create_core_block_registry


@dataclass(frozen=True, slots=True)
class SmokeSceneBlock:
    position: tuple[int, int, int]
    block_key: str


@dataclass(frozen=True, slots=True)
class FoliageSmokeScene:
    key: str
    spawn_position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    blocks: tuple[SmokeSceneBlock, ...]


def build_foliage_smoke_scene(registry: BlockRegistry | None = None) -> FoliageSmokeScene:
    """Build a small cutout-leaf scene with an opaque backdrop behind leaves."""

    registry = registry or create_core_block_registry()
    for key in ("grass", "stone", "veilwood_log", "veilwood_leaves", "gloam_lantern"):
        registry.by_key(key)

    blocks: list[SmokeSceneBlock] = []
    blocks.extend(_filled_rect("grass", x_range=range(4, 13), y=3, z_range=range(3, 10)))
    blocks.extend(_filled_rect("stone", x_range=range(6, 11), y_range=range(4, 9), z=8))
    blocks.extend(_filled_rect("veilwood_leaves", x_range=range(6, 11), y_range=range(4, 9), z=7))
    blocks.extend(SmokeSceneBlock((8, y, 6), "veilwood_log") for y in range(4, 8))
    blocks.append(SmokeSceneBlock((8, 8, 6), "gloam_lantern"))

    return FoliageSmokeScene(
        key="foliage_cutout_smoke",
        spawn_position=(8.5, 4.0, 1.5),
        look_at=(8.5, 6.0, 7.5),
        blocks=tuple(blocks),
    )


def apply_foliage_smoke_scene(
    set_block: Callable[[tuple[int, int, int], int], object],
    registry: BlockRegistry | None = None,
) -> FoliageSmokeScene:
    registry = registry or create_core_block_registry()
    scene = build_foliage_smoke_scene(registry)
    for block in scene.blocks:
        set_block(block.position, registry.by_key(block.block_key).id)
    return scene


def run_preview() -> int:
    registry = create_core_block_registry()
    scene = build_foliage_smoke_scene(registry)
    print(
        f"{scene.key} spawn={scene.spawn_position} look_at={scene.look_at} "
        f"blocks={len(scene.blocks)}"
    )
    print(
        "manual: stand at spawn, look at look_at, apply a Faithful-style pack, "
        "and verify leaf holes reveal the stone backdrop without sorting artifacts."
    )
    for line in _layer_lines(scene.blocks):
        print(line)
    return 0


def _filled_rect(
    block_key: str,
    *,
    x_range: range,
    z_range: range | None = None,
    y_range: range | None = None,
    y: int | None = None,
    z: int | None = None,
) -> Iterable[SmokeSceneBlock]:
    if (y is None) == (y_range is None):
        raise ValueError("Pass exactly one of y or y_range")
    if (z is None) == (z_range is None):
        raise ValueError("Pass exactly one of z or z_range")

    ys = y_range if y_range is not None else range(y or 0, (y or 0) + 1)
    zs = z_range if z_range is not None else range(z or 0, (z or 0) + 1)
    return (
        SmokeSceneBlock((x, block_y, block_z), block_key)
        for x in x_range
        for block_y in ys
        for block_z in zs
    )


def _layer_lines(blocks: tuple[SmokeSceneBlock, ...]) -> Iterable[str]:
    occupied = {block.position: block.block_key for block in blocks}
    keys = {
        "grass": "G",
        "stone": "S",
        "veilwood_leaves": "L",
        "veilwood_log": "W",
        "gloam_lantern": "*",
    }
    xs = range(min(x for x, _y, _z in occupied), max(x for x, _y, _z in occupied) + 1)
    zs = range(min(z for _x, _y, z in occupied), max(z for _x, _y, z in occupied) + 1)
    for y in range(max(y for _x, y, _z in occupied), min(y for _x, y, _z in occupied) - 1, -1):
        if not any(pos_y == y for _x, pos_y, _z in occupied):
            continue
        yield f"layer y={y}"
        for z in zs:
            yield "".join(keys.get(occupied.get((x, y, z), ""), ".") for x in xs)
