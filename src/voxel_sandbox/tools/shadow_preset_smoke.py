from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from voxel_sandbox.app.settings import AppSettings


@dataclass(frozen=True, slots=True)
class ShadowPresetVariant:
    name: str
    quality_preset: str
    shadow_quality: str
    material_quality: str


@dataclass(frozen=True, slots=True)
class ShadowPresetCapture:
    name: str
    quality_preset: str
    shadow_quality: str
    material_quality: str
    screenshot: str
    visible_sections: int
    pending_meshes: int


SHADOW_PRESET_VARIANTS: tuple[ShadowPresetVariant, ...] = (
    ShadowPresetVariant(
        name="off",
        quality_preset="custom",
        shadow_quality="off",
        material_quality="color-only",
    ),
    ShadowPresetVariant(
        name="low",
        quality_preset="custom",
        shadow_quality="low",
        material_quality="color-only",
    ),
    ShadowPresetVariant(
        name="medium",
        quality_preset="custom",
        shadow_quality="medium",
        material_quality="color-only",
    ),
    ShadowPresetVariant(
        name="high_material_preview",
        quality_preset="high",
        shadow_quality="medium",
        material_quality="material-preview",
    ),
)


def shadow_capture_settings(
    settings: AppSettings,
    variant: ShadowPresetVariant,
    *,
    render_distance: int,
) -> AppSettings:
    return replace(
        settings,
        graphics=replace(
            settings.graphics,
            quality_preset=variant.quality_preset,
            shadow_quality=variant.shadow_quality,
            material_quality=variant.material_quality,
        ),
        world=replace(
            settings.world,
            render_distance=render_distance,
            generation_backend="thread",
            meshing_backend="thread",
        ),
    )


def run_shadow_preset_smoke(
    settings: AppSettings,
    *,
    frames: int = 100,
    render_distance: int = 2,
    output_dir: Path | None = None,
) -> int:
    from voxel_sandbox.engine.game_state import GameState
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    root = output_dir or Path("saves/shadow_preset_smoke")
    root.mkdir(parents=True, exist_ok=True)
    previous_data_dir = os.environ.get("VEILSTONE_DATA_DIR")
    captures: list[ShadowPresetCapture] = []
    try:
        for variant in SHADOW_PRESET_VARIANTS:
            variant_root = root / variant.name
            os.environ["VEILSTONE_DATA_DIR"] = str(variant_root)
            run_settings = shadow_capture_settings(
                settings,
                variant,
                render_distance=render_distance,
            )
            window = GameWindow(
                run_settings,
                visible=False,
                save_root=variant_root / "world",
            )
            try:
                window.switch_to()
                window.menu.screen = Screen.GAME
                window.debug_overlay_visible = True
                window.game_state.try_transition(GameState.PLAYING)
                for _ in range(frames):
                    window.fixed_update(1.0 / 60.0)
                    window.on_draw()
                    window.flip()
                window.mgl_context.finish()
                screenshot = window.save_screenshot()
                perf = window.runtime_perf_snapshot
                captures.append(
                    ShadowPresetCapture(
                        name=variant.name,
                        quality_preset=run_settings.graphics.quality_preset,
                        shadow_quality=run_settings.graphics.shadow_quality,
                        material_quality=run_settings.graphics.material_quality,
                        screenshot=str(screenshot),
                        visible_sections=perf.queues.visible_sections,
                        pending_meshes=perf.queues.pending_meshes,
                    )
                )
            finally:
                window.close()
    finally:
        if previous_data_dir is None:
            os.environ.pop("VEILSTONE_DATA_DIR", None)
        else:
            os.environ["VEILSTONE_DATA_DIR"] = previous_data_dir

    metadata_path = root / "shadow_preset_smoke.json"
    metadata_path.write_text(
        json.dumps([asdict(capture) for capture in captures], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"metadata={metadata_path}")
    for capture in captures:
        print(
            f"{capture.name}: preset={capture.quality_preset} "
            f"shadow={capture.shadow_quality} material={capture.material_quality} "
            f"screenshot={capture.screenshot}"
        )
    return 0
