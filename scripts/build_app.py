from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).parents[1]
    separator = ";" if sys.platform == "win32" else ":"
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
    ]
    icon_name = {
        "darwin": "veilstone.icns",
        "win32": "veilstone.ico",
    }.get(sys.platform, "veilstone-icon.png")
    icon = root / "assets/branding" / icon_name
    if icon.exists():
        command.extend(("--icon", str(icon)))
    command.append(str(root / "src/voxel_sandbox/__main__.py"))
    subprocess.run(command, cwd=root, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
