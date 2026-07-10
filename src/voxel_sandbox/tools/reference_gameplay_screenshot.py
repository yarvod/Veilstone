from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, ChunkCoord, split_world_axis
from voxel_sandbox.engine.generation import TerrainGenerator
from voxel_sandbox.tools.reference_gameplay_scene import (
    ReferenceGameplayScene,
    ReferenceSceneBlock,
    build_reference_gameplay_scene,
    summarize_reference_gameplay_scene,
)

if TYPE_CHECKING:
    from voxel_sandbox.render.camera import FirstPersonCamera


@dataclass(frozen=True, slots=True)
class ReferenceRenderLayout:
    scene_key: str
    base_y: int
    camera_position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    blocks: tuple[ReferenceSceneBlock, ...]


@dataclass(frozen=True, slots=True)
class RenderedReferenceMetadata:
    scene_key: str
    seed: int
    screenshot: str
    display_status: str
    resource_pack: str
    render_distance: int
    camera_mode: str
    base_y: int
    camera_position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    block_count: int
    block_counts: dict[str, int]
    placed_block_count: int
    expected_chunks: int
    rebuilt_chunks: int
    visible_sections: int
    water_mesh_sections: int
    water_mesh_triangles: int
    invariants_passed: bool = False


_SCENE_GROUND_Y = 3
_SCENE_CENTER_X = 9.0
_SCENE_CENTER_Z = 8.0


def reference_capture_settings(
    settings: AppSettings,
    *,
    seed: int,
    render_distance: int,
    resource_pack: str,
) -> AppSettings:
    if render_distance < 1:
        raise ValueError("Reference screenshot render distance must be positive")
    return replace(
        settings,
        graphics=replace(
            settings.graphics,
            quality_preset="custom",
            day_cycle_seconds=0.0,
            shadow_quality="medium",
            smooth_lighting=True,
            ambient_occlusion=True,
            clouds=False,
            material_quality="color-only",
            resource_pack_path=None if resource_pack == "default" else resource_pack,
        ),
        world=replace(
            settings.world,
            seed=str(seed),
            render_distance=render_distance,
            generation_backend="thread",
            meshing_backend="thread",
        ),
    )


def choose_reference_scene_base_y(height_at: Callable[[int, int], int]) -> int:
    terrain_top = max(height_at(x, z) for x in range(4, 15) for z in range(4, 13))
    base_y = max(96, terrain_top + 10)
    if base_y > CHUNK_HEIGHT - 8:
        raise RuntimeError("Generated terrain is too tall for the reference scene")
    return base_y


def build_reference_render_layout(
    scene: ReferenceGameplayScene,
    *,
    base_y: int,
) -> ReferenceRenderLayout:
    if not 1 <= base_y <= CHUNK_HEIGHT - 8:
        raise ValueError("Reference scene base height is outside the buildable range")
    offset_y = base_y - _SCENE_GROUND_Y
    blocks = tuple(
        ReferenceSceneBlock(
            (block.position[0], block.position[1] + offset_y, block.position[2]),
            block.block_key,
        )
        for block in scene.blocks
    )
    return ReferenceRenderLayout(
        scene_key=scene.key,
        base_y=base_y,
        camera_position=(1.0, float(base_y) + 11.0, 0.5),
        look_at=(_SCENE_CENTER_X, float(base_y) + 2.0, _SCENE_CENTER_Z),
        blocks=blocks,
    )


def apply_reference_render_layout(
    layout: ReferenceRenderLayout,
    *,
    set_block: Callable[[tuple[int, int, int], int], object],
    registry: BlockRegistry,
) -> int:
    changed = 0
    for block in layout.blocks:
        changed += int(bool(set_block(block.position, registry.by_key(block.block_key).id)))
    return changed


def reference_scene_chunks(layout: ReferenceRenderLayout) -> tuple[ChunkCoord, ...]:
    coordinates = {
        ChunkCoord(split_world_axis(block.position[0])[0], split_world_axis(block.position[2])[0])
        for block in layout.blocks
    }
    return tuple(sorted(coordinates, key=lambda coordinate: (coordinate.x, coordinate.z)))


def camera_angles(
    position: tuple[float, float, float],
    target: tuple[float, float, float],
) -> tuple[float, float]:
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    dz = target[2] - position[2]
    if dx == dy == dz == 0.0:
        raise ValueError("Reference camera target must differ from its position")
    return (
        math.degrees(math.atan2(dz, dx)),
        math.degrees(math.atan2(dy, math.hypot(dx, dz))),
    )


def build_rendered_reference_metadata(
    *,
    scene: ReferenceGameplayScene,
    layout: ReferenceRenderLayout,
    screenshot: Path,
    resource_pack: str,
    render_distance: int,
    placed_block_count: int,
    expected_chunks: int,
    rebuilt_chunks: int,
    visible_sections: int,
    water_mesh_sections: int,
    water_mesh_triangles: int,
) -> RenderedReferenceMetadata:
    summary = summarize_reference_gameplay_scene(scene)
    return RenderedReferenceMetadata(
        scene_key=scene.key,
        seed=scene.seed,
        screenshot=str(screenshot),
        display_status="available",
        resource_pack=resource_pack,
        render_distance=render_distance,
        camera_mode="isometric",
        base_y=layout.base_y,
        camera_position=layout.camera_position,
        look_at=layout.look_at,
        block_count=summary.block_count,
        block_counts=summary.block_counts,
        placed_block_count=placed_block_count,
        expected_chunks=expected_chunks,
        rebuilt_chunks=rebuilt_chunks,
        visible_sections=visible_sections,
        water_mesh_sections=water_mesh_sections,
        water_mesh_triangles=water_mesh_triangles,
    )


def validate_rendered_reference_metadata(
    metadata: RenderedReferenceMetadata,
    scene: ReferenceGameplayScene,
) -> RenderedReferenceMetadata:
    summary = summarize_reference_gameplay_scene(scene)
    if metadata.scene_key != scene.key or metadata.seed != scene.seed:
        raise ValueError("Rendered reference identity does not match its fixture")
    if metadata.display_status != "available" or not metadata.screenshot:
        raise ValueError("Rendered reference requires an available display and screenshot")
    if metadata.camera_mode != "isometric":
        raise ValueError("Rendered reference camera mode is not isometric")
    camera_angles(metadata.camera_position, metadata.look_at)
    if metadata.block_count != summary.block_count or metadata.block_counts != summary.block_counts:
        raise ValueError("Rendered reference block summary does not match its fixture")
    if metadata.placed_block_count != summary.block_count:
        raise ValueError("Rendered reference did not place every fixture block")
    if metadata.expected_chunks < 1 or metadata.rebuilt_chunks != metadata.expected_chunks:
        raise ValueError("Rendered reference did not rebuild every fixture chunk")
    if metadata.visible_sections < 1:
        raise ValueError("Rendered reference did not produce visible mesh sections")
    if metadata.water_mesh_sections < 1 or metadata.water_mesh_triangles < 1:
        raise ValueError("Rendered reference did not produce visible water geometry")
    return replace(metadata, invariants_passed=True)


def write_rendered_reference_metadata(
    path: Path,
    metadata: RenderedReferenceMetadata,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_reference_gameplay_screenshot(
    settings: AppSettings,
    *,
    seed: int = 1337,
    render_distance: int = 2,
    resource_pack: str = "default",
    output_dir: Path | None = None,
) -> int:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        print("reference-gameplay-screenshot: skipped (no active display)")
        return 0

    from voxel_sandbox.app.composition import UserSettingsStore, build_app_runtime
    from voxel_sandbox.engine.game_state import GameState
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    root = output_dir or Path("saves/reference_gameplay_screenshot")
    root.mkdir(parents=True, exist_ok=True)
    scene = build_reference_gameplay_scene(seed=seed)
    run_settings = reference_capture_settings(
        settings,
        seed=seed,
        render_distance=render_distance,
        resource_pack=resource_pack,
    )
    app_runtime = build_app_runtime(
        run_settings,
        data_root=root,
        settings_store=UserSettingsStore(root / "settings.toml"),
    )
    with tempfile.TemporaryDirectory(
        prefix="veilstone-reference-scene-world-",
        dir=root,
    ) as world_directory:
        window = GameWindow(
            run_settings,
            visible=False,
            save_root=Path(world_directory),
            app_runtime=app_runtime,
        )
        try:
            renderer = window.world_renderer
            renderer.ensure_collision_area_loaded(_SCENE_CENTER_X, _SCENE_CENTER_Z, 0.0)
            registry = cast(BlockRegistry, window.world_runtime.block_registry)
            generation = cast(TerrainGenerator, window.world_runtime.generation)
            layout = build_reference_render_layout(
                scene,
                base_y=choose_reference_scene_base_y(generation.height_at),
            )
            placed_blocks = apply_reference_render_layout(
                layout,
                set_block=renderer.set_block,
                registry=registry,
            )
            coordinates = reference_scene_chunks(layout)
            rebuilt_chunks = renderer.rebuild_loaded_chunk_meshes_sync(coordinates)

            window.camera.position = layout.camera_position
            _look_at(window.camera, layout.look_at)
            window.menu.screen = Screen.GAME
            window.hud_hidden = True
            # The reference frame is scene-only; this suppresses the first-person
            # hand while the hidden HUD keeps the inventory panel out of the frame.
            window.inventory_open = True
            window.game_state.try_transition(GameState.PLAYING)
            renderer.time_of_day = 0.32
            window.switch_to()
            for _ in range(3):
                window.on_draw()
                window.flip()
            window.mgl_context.finish()
            screenshot = window.save_screenshot()
            queues = renderer.perf_queues()
            metadata = validate_rendered_reference_metadata(
                build_rendered_reference_metadata(
                    scene=scene,
                    layout=layout,
                    screenshot=screenshot,
                    resource_pack=resource_pack,
                    render_distance=render_distance,
                    placed_block_count=placed_blocks,
                    expected_chunks=len(coordinates),
                    rebuilt_chunks=rebuilt_chunks,
                    visible_sections=queues.visible_sections,
                    water_mesh_sections=renderer.water_mesh_sections,
                    water_mesh_triangles=renderer.water_mesh_triangles,
                ),
                scene,
            )
            metadata_path = root / "reference_gameplay_screenshot.json"
            write_rendered_reference_metadata(metadata_path, metadata)
            print(f"scene={scene.key}")
            print(f"screenshot={screenshot}")
            print(f"metadata={metadata_path}")
            print(
                f"blocks={metadata.placed_block_count} "
                f"chunks={metadata.rebuilt_chunks} "
                f"visible_sections={metadata.visible_sections} "
                f"water_triangles={metadata.water_mesh_triangles}"
            )
        finally:
            window.close()
    return 0


def _look_at(camera: FirstPersonCamera, target: tuple[float, float, float]) -> None:
    camera.yaw_degrees, camera.pitch_degrees = camera_angles(camera.position, target)
