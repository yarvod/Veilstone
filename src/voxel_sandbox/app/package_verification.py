from __future__ import annotations

from pathlib import Path

from voxel_sandbox.app.paths import resource_path, user_settings_path
from voxel_sandbox.app.settings import load_settings, save_user_settings


def missing_package_resources() -> tuple[Path, ...]:
    package_root = Path(__file__).parents[1]
    required = (
        resource_path("config/settings.toml"),
        resource_path("config/recipes.toml"),
        resource_path("config/audio.toml"),
        resource_path("assets/audio/ui_click.wav"),
        resource_path("assets/audio/music_exploration.wav"),
        package_root / "render/shaders/glsl/chunk_opaque.vert",
        package_root / "render/shaders/glsl/chunk_opaque.frag",
        package_root / "render/shaders/glsl/entity.vert",
        package_root / "render/shaders/glsl/entity.frag",
        package_root / "engine/generation/structure_templates/veilstone_ruin.toml",
    )
    return tuple(path for path in required if not path.is_file())


def verify_package() -> int:
    missing = missing_package_resources()
    if missing:
        print("Missing packaged resources:")
        for path in missing:
            print(path)
        return 1

    settings = load_settings()
    save_user_settings(settings)
    if not user_settings_path().is_file():
        print(f"Unable to create user settings: {user_settings_path()}")
        return 1
    print("Package resources and user-data path verified")
    return 0
