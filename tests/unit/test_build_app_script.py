from __future__ import annotations

import tomllib
from pathlib import Path

from scripts.build_app import build_command


def _add_data_values(command: list[str]) -> list[str]:
    return [command[index + 1] for index, value in enumerate(command) if value == "--add-data"]


def test_build_command_packages_data_directory_on_macos(tmp_path: Path) -> None:
    command = build_command(tmp_path, platform="darwin")

    assert f"{tmp_path / 'data'}:data" in _add_data_values(command)


def test_build_command_packages_data_directory_on_windows(tmp_path: Path) -> None:
    command = build_command(tmp_path, platform="win32")

    assert f"{tmp_path / 'data'};data" in _add_data_values(command)


def test_wheel_package_includes_data_resources() -> None:
    with open("pyproject.toml", "rb") as pyproject:
        metadata = tomllib.load(pyproject)

    force_include = metadata["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["data"] == "voxel_sandbox/resources/data"
