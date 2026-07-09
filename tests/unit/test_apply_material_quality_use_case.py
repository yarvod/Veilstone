from __future__ import annotations

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.application.material_quality import ApplyMaterialQualityUseCase


class FakeRenderer:
    def __init__(self) -> None:
        self.applied: list[tuple[str, str]] = []

    def apply_material_quality(self, material_quality: str, resource_pack_path: str = "") -> None:
        self.applied.append((material_quality, resource_pack_path))


class FakeSettingsStore:
    def __init__(self) -> None:
        self.saved: AppSettings | None = None

    def save(self, settings: AppSettings) -> None:
        self.saved = settings


def test_apply_material_quality_updates_renderer_and_settings() -> None:
    renderer = FakeRenderer()
    store = FakeSettingsStore()
    settings = AppSettings()

    result = ApplyMaterialQualityUseCase(settings_store=store).execute(
        quality="material-preview",
        settings=settings,
        renderer=renderer,
    )

    assert result.applied is True
    assert result.settings.graphics.material_quality == "material-preview"
    assert renderer.applied == [("material-preview", settings.graphics.resource_pack_path)]
    assert store.saved is result.settings
    assert "material-preview" in result.status


def test_apply_material_quality_rejects_unknown_profile() -> None:
    renderer = FakeRenderer()
    store = FakeSettingsStore()
    settings = AppSettings()

    result = ApplyMaterialQualityUseCase(settings_store=store).execute(
        quality="ultra",
        settings=settings,
        renderer=renderer,
    )

    assert result.applied is False
    assert result.settings is settings
    assert renderer.applied == []
    assert store.saved is None


def test_apply_material_quality_normalizes_input_case() -> None:
    renderer = FakeRenderer()
    store = FakeSettingsStore()

    result = ApplyMaterialQualityUseCase(settings_store=store).execute(
        quality="  Color-Only ",
        settings=AppSettings(),
        renderer=renderer,
    )

    assert result.applied is True
    assert result.settings.graphics.material_quality == "color-only"
