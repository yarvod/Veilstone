from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from voxel_sandbox.app.settings import AppSettings, load_settings, save_user_settings


def test_missing_settings_file_uses_defaults(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.toml")
    assert settings == AppSettings()
    assert settings.development.render_local_player_model is False
    assert settings.graphics.material_quality == "color-only"


def test_settings_are_loaded_from_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        '[window]\ntitle = "Test World"\nwidth = 800\n[graphics]\nmaterial_quality = "low"\n',
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.window.title == "Test World"
    assert settings.window.width == 800
    assert settings.window.height == 720
    assert settings.graphics.material_quality == "low"


def test_user_settings_roundtrip(tmp_path: Path) -> None:
    settings = AppSettings()
    settings = replace(
        settings,
        graphics=replace(
            settings.graphics,
            shadow_quality="off",
            clouds=False,
            material_quality="material-preview",
        ),
        window=replace(settings.window, vsync=False),
        world=replace(settings.world, seed="saved-seed", render_distance=5),
        gameplay=replace(settings.gameplay, difficulty="peaceful", hostile_spawn_light_limit=5),
        audio=replace(settings.audio, master=0.3, music=0.2, ambience=0.4),
        controls=replace(settings.controls, forward="UP", jump="RSHIFT"),
    )
    path = tmp_path / "settings.toml"

    save_user_settings(settings, path)
    loaded = load_settings(path)

    assert loaded.graphics.shadow_quality == "off"
    assert not loaded.graphics.clouds
    assert loaded.graphics.material_quality == "material-preview"
    assert not loaded.window.vsync
    assert loaded.world.seed == "saved-seed"
    assert loaded.world.render_distance == 5
    assert loaded.gameplay.difficulty == "peaceful"
    assert loaded.gameplay.hostile_spawn_light_limit == 5
    assert loaded.audio.master == 0.3
    assert loaded.audio.effects == settings.audio.effects
    assert loaded.audio.music == 0.2
    assert loaded.audio.ambience == 0.4
    assert loaded.controls.forward == "UP"
    assert loaded.controls.jump == "RSHIFT"
