from __future__ import annotations

from pathlib import Path

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.application.resource_packs import ApplyResourcePackUseCase


class FakeRenderer:
    def __init__(self) -> None:
        self.registry = object()
        self.applied_atlas: object | None = None

    def apply_texture_pack(self, atlas: object) -> None:
        self.applied_atlas = atlas


class FakeSettingsStore:
    def __init__(self) -> None:
        self.saved: AppSettings | None = None

    def save(self, settings: AppSettings) -> None:
        self.saved = settings


def test_apply_resource_pack_updates_renderer_and_settings(tmp_path: Path) -> None:
    atlas = object()
    renderer = FakeRenderer()
    store = FakeSettingsStore()
    pack = tmp_path / "pack"
    pack.mkdir()
    calls: list[tuple[Path | None, object, Path]] = []

    def load_atlas(
        path: Path | None,
        *,
        registry: object,
        cache_root: Path,
    ) -> object:
        calls.append((path, registry, cache_root))
        return atlas

    use_case = ApplyResourcePackUseCase(load_atlas, store)

    result = use_case.execute(
        path=str(pack),
        settings=AppSettings(),
        renderer=renderer,
        cache_root=tmp_path / "cache",
    )

    assert result.applied
    assert result.status == f"Resource pack applied: {pack}"
    assert result.settings.graphics.resource_pack_path == str(pack)
    assert store.saved is result.settings
    assert renderer.applied_atlas is atlas
    assert calls == [(pack, renderer.registry, tmp_path / "cache")]


def test_apply_resource_pack_reset_uses_default_atlas(tmp_path: Path) -> None:
    atlas = object()
    renderer = FakeRenderer()
    store = FakeSettingsStore()

    use_case = ApplyResourcePackUseCase(lambda *args, **kwargs: atlas, store)

    result = use_case.execute(
        path=None,
        settings=AppSettings(),
        renderer=renderer,
        cache_root=tmp_path / "cache",
    )

    assert result.applied
    assert result.status == "Resource pack reset to default."
    assert result.settings.graphics.resource_pack_path == ""
    assert store.saved is result.settings
    assert renderer.applied_atlas is atlas


def test_apply_resource_pack_missing_path_does_not_mutate(tmp_path: Path) -> None:
    renderer = FakeRenderer()
    store = FakeSettingsStore()

    use_case = ApplyResourcePackUseCase(lambda *args, **kwargs: object(), store)

    settings = AppSettings()
    result = use_case.execute(
        path=str(tmp_path / "missing"),
        settings=settings,
        renderer=renderer,
        cache_root=tmp_path / "cache",
    )

    assert not result.applied
    assert result.settings is settings
    assert result.status.startswith("Resource pack not found:")
    assert store.saved is None
    assert renderer.applied_atlas is None
