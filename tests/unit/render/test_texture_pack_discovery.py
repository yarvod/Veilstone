from __future__ import annotations

import json
import zipfile
from pathlib import Path

from voxel_sandbox.render.texture_packs.discovery import discover_texture_packs


def test_discover_texture_packs_lists_default_folder_and_zip(tmp_path: Path) -> None:
    folder_pack = tmp_path / "FolderPack"
    folder_pack.mkdir()
    (folder_pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"pack_format": 18, "description": "folder"}}),
        encoding="utf-8",
    )

    zip_pack = tmp_path / "ZipPack.zip"
    with zipfile.ZipFile(zip_pack, "w") as zf:
        zf.writestr(
            "pack.mcmeta",
            json.dumps({"pack": {"pack_format": 18, "description": "zip"}}),
        )

    (tmp_path / "README.md").write_text("ignored", encoding="utf-8")
    (tmp_path / "NotAPack").mkdir()

    packs = discover_texture_packs(tmp_path)

    assert packs == [
        ("Default", None),
        ("FolderPack", folder_pack),
        ("ZipPack.zip", zip_pack),
    ]


def test_discover_texture_packs_missing_root_returns_default(tmp_path: Path) -> None:
    assert discover_texture_packs(tmp_path / "missing") == [("Default", None)]
