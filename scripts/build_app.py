from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def build_command(root: Path, platform: str = sys.platform) -> list[str]:
    separator = ";" if platform == "win32" else ":"
    command = [
        "uv",
        "run",
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "Veilstone",
        "--paths",
        str(root / "src"),
        "--add-data",
        f"{root / 'src/voxel_sandbox/render/shaders'}{separator}voxel_sandbox/render/shaders",
        "--add-data",
        f"{root / 'src/voxel_sandbox/engine/generation/structure_templates'}"
        f"{separator}voxel_sandbox/engine/generation/structure_templates",
        "--add-data",
        f"{root / 'config'}{separator}config",
        "--add-data",
        f"{root / 'assets'}{separator}assets",
        "--add-data",
        f"{root / 'data'}{separator}data",
        "--add-data",
        f"{root / 'resource_packs'}{separator}resource_packs",
    ]
    icon_name = {
        "darwin": "veilstone.icns",
        "win32": "veilstone.ico",
    }.get(platform, "veilstone-icon.png")
    icon = root / "assets/branding" / icon_name
    if icon.exists():
        command.extend(("--icon", str(icon)))
    command.append(str(root / "src/voxel_sandbox/__main__.py"))
    return command


def main() -> int:
    root = Path(__file__).parents[1]
    subprocess.run(build_command(root), cwd=root, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
