# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownLambdaType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.render.menu_ui import MenuUI
from voxel_sandbox.render.texture_atlas import GeneratedAtlas
from voxel_sandbox.render.texture_packs.models import ImportReport


def test_apply_selected_texture_pack_applies_atlas_and_saves_settings(tmp_path: Path) -> None:
    pack = tmp_path / "Pack"
    pack.mkdir()
    atlas = GeneratedAtlas(1, 1, b"\x00\x00\x00\xff", {})
    saved_settings: list[AppSettings] = []

    class FakeTexturePackService:
        def discover(self, root: Path) -> list[tuple[str, Path | None]]:
            return [("Pack", pack)]

        def load_block_atlas(
            self,
            path: Path | None,
            *,
            registry: object,
            report_callback=None,
            cache_root: Path | None = None,
        ) -> GeneratedAtlas:
            assert path == pack
            assert registry == "registry"
            assert cache_root == win.active_save_root.parent / "texture_cache"
            if report_callback is not None:
                report_callback(
                    ImportReport(
                        pack_id="Pack",
                        imported=["minecraft:block/stone"],
                        fallback=["minecraft:block/dirt"],
                        missing=["minecraft:block/grass_block_top"],
                    )
                )
            return atlas

    applied: list[GeneratedAtlas] = []
    win = SimpleNamespace(
        menu=SimpleNamespace(status=""),
        settings=AppSettings(),
        app_runtime=SimpleNamespace(
            settings_store=SimpleNamespace(save=lambda settings: saved_settings.append(settings)),
            texture_packs=FakeTexturePackService(),
        ),
        active_save_root=tmp_path / "save",
        world_runtime=SimpleNamespace(block_registry="registry"),
        world_renderer=SimpleNamespace(
            apply_texture_pack=lambda next_atlas: applied.append(next_atlas),
        ),
    )
    menu_ui = MenuUI.__new__(MenuUI)
    menu_ui.win = win
    menu_ui.texture_pack_items = [("Default", None), ("Pack", pack)]
    menu_ui.texture_pack_index = 1

    menu_ui._apply_selected_texture_pack()

    assert applied == [atlas]
    assert saved_settings == [win.settings]
    assert win.settings.graphics.resource_pack_path == str(pack)
    assert win.menu.status == "Texture pack applied: Pack (1 fallback, 1 missing)."


def test_texture_pack_root_uses_app_data_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "voxel_sandbox.render.menu_ui.resource_packs_root",
        lambda: tmp_path / "resource_packs",
    )

    menu_ui = MenuUI.__new__(MenuUI)

    assert menu_ui._resource_packs_dir() == tmp_path / "resource_packs"


def test_texture_pack_discovery_has_single_default_and_local_packs(
    tmp_path: Path, monkeypatch
) -> None:
    app_root = tmp_path / "data_packs"
    legacy_root = tmp_path / "legacy_packs"
    app_default = app_root / "default"
    app_pack = app_root / "AppPack"
    legacy_default = legacy_root / "default"
    legacy_pack = legacy_root / "Faithful-32x-1.21.11"
    app_default.mkdir(parents=True)
    app_pack.mkdir(parents=True)
    legacy_default.mkdir(parents=True)
    legacy_pack.mkdir(parents=True)

    monkeypatch.setattr(
        "voxel_sandbox.render.menu_ui.resource_packs_root",
        lambda: app_root,
    )

    class FakeTexturePackService:
        def discover(self, root: Path) -> list[tuple[str, Path | None]]:
            if root == app_root:
                return [("default", app_default), ("AppPack", app_pack)]
            if root == legacy_root:
                return [
                    ("default", legacy_default),
                    ("Faithful-32x-1.21.11", legacy_pack),
                ]
            return []

    menu_ui = MenuUI.__new__(MenuUI)
    menu_ui.win = SimpleNamespace(
        app_runtime=SimpleNamespace(texture_packs=FakeTexturePackService())
    )
    monkeypatch.setattr(menu_ui, "_legacy_resource_packs_dir", lambda: legacy_root)

    assert menu_ui._discover_texture_packs() == [
        ("Default", None),
        ("AppPack", app_pack),
        ("Faithful-32x-1.21.11", legacy_pack),
    ]


def test_texture_pack_status_names_cached_non_default_pack() -> None:
    menu_ui = MenuUI.__new__(MenuUI)

    assert menu_ui._texture_pack_status("Default", None) == "Default texture pack applied."
    assert (
        menu_ui._texture_pack_status("Faithful-32x-1.21.11", None)
        == "Texture pack applied: Faithful-32x-1.21.11."
    )
