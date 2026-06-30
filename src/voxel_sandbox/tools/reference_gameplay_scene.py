from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from voxel_sandbox.domain.blocks import BlockRegistry, create_core_block_registry
from voxel_sandbox.domain.items import ItemRegistry, create_core_item_registry


@dataclass(frozen=True, slots=True)
class ReferenceSceneBlock:
    position: tuple[int, int, int]
    block_key: str


@dataclass(frozen=True, slots=True)
class ReferenceSceneMob:
    mob_key: str
    spawn_position: tuple[float, float, float]
    path: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True, slots=True)
class ReferenceInventoryIcon:
    slot: int
    item_key: str
    count: int


@dataclass(frozen=True, slots=True)
class ReferenceFirstPersonInteraction:
    hand: str
    item_key: str
    interaction: str
    progress: float


@dataclass(frozen=True, slots=True)
class ReferenceGameplayScene:
    key: str
    seed: int
    spawn_position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    blocks: tuple[ReferenceSceneBlock, ...]
    mobs: tuple[ReferenceSceneMob, ...]
    inventory_icons: tuple[ReferenceInventoryIcon, ...]
    first_person_interaction: ReferenceFirstPersonInteraction
    features: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReferenceSceneSummary:
    scene_key: str
    seed: int
    block_count: int
    block_counts: dict[str, int]
    mob_count: int
    inventory_icon_count: int
    features: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReferenceCaptureMetadata:
    scene_key: str
    seed: int
    resource_pack: str
    render_distance: int
    settings_profile: str
    camera_mode: str
    summary: ReferenceSceneSummary


def build_reference_gameplay_scene(
    *,
    seed: int = 1337,
    block_registry: BlockRegistry | None = None,
    item_registry: ItemRegistry | None = None,
) -> ReferenceGameplayScene:
    blocks = block_registry or create_core_block_registry()
    items = item_registry or create_core_item_registry()
    for key in (
        "grass",
        "stone",
        "water",
        "oak_log",
        "oak_leaves",
        "gloam_lantern",
        "short_grass",
        "wildflower",
        "crafting_table",
    ):
        blocks.by_key(key)
    for key in ("grass_block", "oak_planks", "water_vessel", "dusk_crystal", "crafting_table"):
        items.by_key(key)

    scene_blocks: list[ReferenceSceneBlock] = []
    scene_blocks.extend(_filled_rect("grass", x_range=range(4, 15), y=3, z_range=range(4, 13)))
    scene_blocks.extend(_filled_rect("water", x_range=range(5, 9), y=4, z_range=range(5, 8)))
    scene_blocks.extend(_filled_rect("stone", x_range=range(10, 14), y=4, z_range=range(8, 12)))
    scene_blocks.extend(ReferenceSceneBlock((12, y, 7), "oak_log") for y in range(4, 8))
    scene_blocks.extend(
        _filled_rect("oak_leaves", x_range=range(10, 15), y=8, z_range=range(5, 10))
    )
    scene_blocks.append(ReferenceSceneBlock((12, 8, 7), "gloam_lantern"))
    scene_blocks.append(ReferenceSceneBlock((7, 4, 10), "short_grass"))
    scene_blocks.append(ReferenceSceneBlock((8, 4, 10), "wildflower"))
    scene_blocks.append(ReferenceSceneBlock((10, 4, 6), "crafting_table"))

    return ReferenceGameplayScene(
        key="reference_gameplay_snapshot",
        seed=seed,
        spawn_position=(8.5, 5.0, 2.5),
        look_at=(10.5, 5.5, 8.5),
        blocks=tuple(scene_blocks),
        mobs=(
            ReferenceSceneMob(
                "zombie",
                (13.5, 5.0, 10.5),
                ((13.5, 5.0, 10.5), (11.5, 5.0, 9.5), (13.5, 5.0, 8.5)),
            ),
            ReferenceSceneMob(
                "cow",
                (6.5, 5.0, 11.5),
                ((6.5, 5.0, 11.5), (8.5, 5.0, 11.0), (7.5, 5.0, 9.5)),
            ),
        ),
        inventory_icons=(
            ReferenceInventoryIcon(0, "grass_block", 16),
            ReferenceInventoryIcon(1, "oak_planks", 32),
            ReferenceInventoryIcon(2, "water_vessel", 1),
            ReferenceInventoryIcon(3, "dusk_crystal", 5),
            ReferenceInventoryIcon(4, "crafting_table", 1),
        ),
        first_person_interaction=ReferenceFirstPersonInteraction(
            hand="right",
            item_key="crafting_table",
            interaction="place",
            progress=0.65,
        ),
        features=(
            "water",
            "foliage",
            "lighting",
            "mob_movement",
            "inventory_icons",
            "first_person_interaction",
        ),
    )


def summarize_reference_gameplay_scene(
    scene: ReferenceGameplayScene,
) -> ReferenceSceneSummary:
    block_counts = dict(sorted(Counter(block.block_key for block in scene.blocks).items()))
    return ReferenceSceneSummary(
        scene_key=scene.key,
        seed=scene.seed,
        block_count=len(scene.blocks),
        block_counts=block_counts,
        mob_count=len(scene.mobs),
        inventory_icon_count=len(scene.inventory_icons),
        features=scene.features,
    )


def build_capture_metadata(
    scene: ReferenceGameplayScene,
    *,
    resource_pack: str,
    render_distance: int,
    settings_profile: str,
    camera_mode: str = "isometric",
) -> ReferenceCaptureMetadata:
    return ReferenceCaptureMetadata(
        scene_key=scene.key,
        seed=scene.seed,
        resource_pack=resource_pack,
        render_distance=render_distance,
        settings_profile=settings_profile,
        camera_mode=camera_mode,
        summary=summarize_reference_gameplay_scene(scene),
    )


def write_capture_metadata(path: Path, metadata: ReferenceCaptureMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_preview(
    *,
    metadata_path: Path | None = None,
    seed: int = 1337,
    resource_pack: str = "default",
    render_distance: int = 3,
    settings_profile: str = "dev-reference",
) -> int:
    scene = build_reference_gameplay_scene(seed=seed)
    summary = summarize_reference_gameplay_scene(scene)
    metadata = build_capture_metadata(
        scene,
        resource_pack=resource_pack,
        render_distance=render_distance,
        settings_profile=settings_profile,
    )
    print(f"scene={summary.scene_key} seed={summary.seed}")
    print(f"features={','.join(summary.features)}")
    print(f"blocks={summary.block_count} counts={summary.block_counts}")
    print(f"mobs={summary.mob_count} inventory_icons={summary.inventory_icon_count}")
    print(
        "capture="
        f"resource_pack={metadata.resource_pack} "
        f"render_distance={metadata.render_distance} "
        f"settings={metadata.settings_profile} "
        f"camera={metadata.camera_mode}"
    )
    if metadata_path is not None:
        write_capture_metadata(metadata_path, metadata)
        print(f"metadata={metadata_path}")
    return 0


def _filled_rect(
    block_key: str,
    *,
    x_range: range,
    y: int,
    z_range: range,
) -> tuple[ReferenceSceneBlock, ...]:
    return tuple(ReferenceSceneBlock((x, y, z), block_key) for x in x_range for z in z_range)
