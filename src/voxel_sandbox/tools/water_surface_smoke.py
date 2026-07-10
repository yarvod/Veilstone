from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.items import ItemStack
from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, ChunkCoord, split_world_axis
from voxel_sandbox.engine.ecs import EntitySimulation
from voxel_sandbox.engine.generation import TerrainGenerator
from voxel_sandbox.engine.physics import PlayerController

if TYPE_CHECKING:
    from voxel_sandbox.render.camera import FirstPersonCamera


@dataclass(frozen=True, slots=True)
class WaterSmokeVariant:
    name: str
    quality_preset: str
    shadow_quality: str = "off"
    smooth_lighting: bool = False
    ambient_occlusion: bool = False
    clouds: bool = False
    material_quality: str = "color-only"


@dataclass(frozen=True, slots=True)
class WaterSmokeBlock:
    position: tuple[int, int, int]
    block_key: str


@dataclass(frozen=True, slots=True)
class WaterSmokeScene:
    key: str
    camera_position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    item_position: tuple[float, float, float]
    water_surface_y: float
    blocks: tuple[WaterSmokeBlock, ...]


@dataclass(frozen=True, slots=True)
class ItemStability:
    item_y: float
    item_vy: float
    last_jitter: float


@dataclass(frozen=True, slots=True)
class WaterSmokeCapture:
    name: str
    quality_preset: str
    shadow_quality: str
    water_detail_enabled: bool
    scene: str
    frames: int
    screenshot: str
    item_y: float
    item_vy: float
    last_jitter: float
    water_surface_y: float
    water_mesh_sections: int
    water_mesh_triangles: int
    visible_sections: int
    pending_meshes: int


WATER_SMOKE_VARIANTS: tuple[WaterSmokeVariant, ...] = (
    WaterSmokeVariant(name="low_60", quality_preset="low_60"),
    WaterSmokeVariant(name="detailed", quality_preset="custom"),
)

_SCENE_X_RANGE = range(3, 14)
_SCENE_Z_RANGE = range(5, 16)
_POOL_X_RANGE = range(4, 13)
_POOL_Z_RANGE = range(6, 15)


def water_capture_settings(
    settings: AppSettings,
    variant: WaterSmokeVariant,
    *,
    render_distance: int,
) -> AppSettings:
    return replace(
        settings,
        graphics=replace(
            settings.graphics,
            quality_preset=variant.quality_preset,
            day_cycle_seconds=0.0,
            shadow_quality=variant.shadow_quality,
            smooth_lighting=variant.smooth_lighting,
            ambient_occlusion=variant.ambient_occlusion,
            clouds=variant.clouds,
            material_quality=variant.material_quality,
        ),
        world=replace(
            settings.world,
            seed="veilstone-water-smoke",
            render_distance=render_distance,
            generation_backend="thread",
            meshing_backend="thread",
        ),
    )


def choose_water_scene_base_y(height_at: Callable[[int, int], int]) -> int:
    terrain_top = max(
        height_at(x, z)
        for x in range(_SCENE_X_RANGE.start - 1, _SCENE_X_RANGE.stop + 1)
        for z in range(1, _SCENE_Z_RANGE.stop + 1)
    )
    base_y = max(96, terrain_top + 10)
    if base_y > CHUNK_HEIGHT - 8:
        raise RuntimeError("Generated terrain is too tall for the water smoke scene")
    return base_y


def build_water_smoke_scene(*, base_y: int) -> WaterSmokeScene:
    if not 1 <= base_y <= CHUNK_HEIGHT - 8:
        raise ValueError("Water smoke base height is outside the buildable scene range")

    blocks = [
        WaterSmokeBlock((x, base_y, z), "stone") for x in _SCENE_X_RANGE for z in _SCENE_Z_RANGE
    ]
    blocks.extend(
        WaterSmokeBlock((x, base_y + 1, z), "stone")
        for x in _SCENE_X_RANGE
        for z in _SCENE_Z_RANGE
        if x in {_SCENE_X_RANGE.start, _SCENE_X_RANGE.stop - 1}
        or z in {_SCENE_Z_RANGE.start, _SCENE_Z_RANGE.stop - 1}
    )
    blocks.extend(
        WaterSmokeBlock((x, base_y + 1, z), "water") for x in _POOL_X_RANGE for z in _POOL_Z_RANGE
    )
    return WaterSmokeScene(
        key="water_surface_smoke",
        camera_position=(8.5, base_y + 5.2, 2.5),
        look_at=(8.5, base_y + 1.9, 10.0),
        item_position=(8.5, base_y + 2.05, 10.5),
        water_surface_y=float(base_y + 2),
        blocks=tuple(blocks),
    )


def apply_water_smoke_scene(
    set_block: Callable[[tuple[int, int, int], int], object],
    registry: BlockRegistry,
    *,
    base_y: int,
) -> WaterSmokeScene:
    scene = build_water_smoke_scene(base_y=base_y)
    for block in scene.blocks:
        set_block(block.position, registry.by_key(block.block_key).id)
    return scene


def summarize_item_stability(
    samples: Sequence[float],
    *,
    item_y: float,
    item_vy: float,
    tail_size: int = 30,
) -> ItemStability:
    if not samples:
        raise ValueError("Item stability requires at least one sample")
    tail = samples[-max(1, tail_size) :]
    return ItemStability(
        item_y=round(item_y, 4),
        item_vy=round(item_vy, 4),
        last_jitter=round(max(tail) - min(tail), 4),
    )


def run_water_surface_smoke(
    settings: AppSettings,
    *,
    frames: int = 180,
    render_distance: int = 2,
    output_dir: Path | None = None,
) -> int:
    import pyglet

    if frames <= 0:
        raise ValueError("Water smoke frames must be positive")
    if not pyglet.display.get_display().get_screens():
        print("water-surface-smoke: skipped (no active display)")
        return 0

    from voxel_sandbox.app.composition import build_app_runtime
    from voxel_sandbox.engine.game_state import GameState
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    root = output_dir or Path("saves/water_surface_smoke")
    root.mkdir(parents=True, exist_ok=True)
    captures: list[WaterSmokeCapture] = []
    for variant in WATER_SMOKE_VARIANTS:
        variant_root = root / variant.name
        variant_root.mkdir(parents=True, exist_ok=True)
        run_settings = water_capture_settings(
            settings,
            variant,
            render_distance=render_distance,
        )
        app_runtime = build_app_runtime(run_settings, data_root=variant_root)
        with tempfile.TemporaryDirectory(
            prefix="veilstone-water-smoke-world-",
            dir=variant_root,
        ) as world_directory:
            window = GameWindow(
                run_settings,
                visible=False,
                save_root=Path(world_directory),
                app_runtime=app_runtime,
            )
            try:
                renderer = window.world_renderer
                renderer.ensure_collision_area_loaded(8.5, 9.5, 0.0)
                registry = cast(BlockRegistry, window.world_runtime.block_registry)
                generation = cast(TerrainGenerator, window.world_runtime.generation)
                simulation = cast(EntitySimulation, window.world_runtime.entity_simulation)
                player = cast(PlayerController, window.world_runtime.player_state)
                base_y = choose_water_scene_base_y(generation.height_at)
                scene = apply_water_smoke_scene(
                    renderer.set_block,
                    registry,
                    base_y=base_y,
                )
                scene_chunks = _scene_chunk_coordinates(scene)
                rebuilt_chunks = renderer.rebuild_loaded_chunk_meshes_sync(scene_chunks)
                if rebuilt_chunks != len(scene_chunks) or renderer.water_mesh_triangles <= 0:
                    raise RuntimeError("Water smoke scene did not produce a visible water mesh")

                player.x = scene.camera_position[0]
                player.y = scene.camera_position[1] - player.eye_height
                player.z = scene.camera_position[2]
                window.camera.position = scene.camera_position
                _look_at(window.camera, scene.look_at)
                window.menu.screen = Screen.GAME
                window.debug_overlay_visible = True
                window.game_state.try_transition(GameState.PLAYING)
                window.switch_to()

                item = simulation.spawn_item(scene.item_position, ItemStack(1, 1))
                samples: list[float] = []

                is_fluid = partial(_block_is_fluid, registry, renderer.get_block)

                for _ in range(frames):
                    renderer.update(1.0 / 60.0)
                    simulation.update(
                        1.0 / 60.0,
                        (player.x, player.y, player.z),
                        generation.height_at,
                        is_fluid,
                        renderer.is_solid_block,
                    )
                    samples.append(simulation.world.transforms[item].y)
                    window.on_draw()
                    window.flip()

                window.mgl_context.finish()
                screenshot = window.save_screenshot()
                transform = simulation.world.transforms[item]
                velocity = simulation.world.velocities[item]
                stability = summarize_item_stability(
                    samples,
                    item_y=transform.y,
                    item_vy=velocity.y,
                )
                queues = renderer.perf_queues()
                captures.append(
                    WaterSmokeCapture(
                        name=variant.name,
                        quality_preset=variant.quality_preset,
                        shadow_quality=renderer.shadow_quality,
                        water_detail_enabled=renderer.water_detail_enabled,
                        scene=scene.key,
                        frames=frames,
                        screenshot=str(screenshot),
                        item_y=stability.item_y,
                        item_vy=stability.item_vy,
                        last_jitter=stability.last_jitter,
                        water_surface_y=scene.water_surface_y,
                        water_mesh_sections=renderer.water_mesh_sections,
                        water_mesh_triangles=renderer.water_mesh_triangles,
                        visible_sections=queues.visible_sections,
                        pending_meshes=queues.pending_meshes,
                    )
                )
            finally:
                window.close()

    metadata_path = root / "water_surface_smoke.json"
    metadata_path.write_text(
        json.dumps([asdict(capture) for capture in captures], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"metadata={metadata_path}")
    for capture in captures:
        print(
            f"{capture.name}: water_detail={str(capture.water_detail_enabled).lower()} "
            f"item_y={capture.item_y:.4f} item_vy={capture.item_vy:.4f} "
            f"jitter={capture.last_jitter:.4f} "
            f"water_triangles={capture.water_mesh_triangles} "
            f"screenshot={capture.screenshot}"
        )
    return 0


def _block_is_fluid(
    registry: BlockRegistry,
    get_block: Callable[[int, int, int], int],
    x: int,
    y: int,
    z: int,
) -> bool:
    return registry.by_id(get_block(x, y, z)).is_fluid


def _scene_chunk_coordinates(scene: WaterSmokeScene) -> tuple[ChunkCoord, ...]:
    coordinates = {
        ChunkCoord(split_world_axis(block.position[0])[0], split_world_axis(block.position[2])[0])
        for block in scene.blocks
    }
    return tuple(sorted(coordinates, key=lambda coord: (coord.x, coord.z)))


def _look_at(camera: FirstPersonCamera, target: tuple[float, float, float]) -> None:
    position = camera.position
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    dz = target[2] - position[2]
    camera.yaw_degrees = math.degrees(math.atan2(dz, dx))
    camera.pitch_degrees = math.degrees(math.atan2(dy, math.hypot(dx, dz)))
