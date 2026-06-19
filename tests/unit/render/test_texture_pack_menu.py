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
            return [("Default", None), ("Pack", pack)]

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
        world_renderer=SimpleNamespace(
            registry="registry",
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
