from __future__ import annotations

import subprocess
import sys


def _workflow_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *sys.argv[1:]],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(result.stdout, end="")
    if result.returncode:
        summary = result.stdout[-12_000:]
        print(f"::error title=pytest failed::{_workflow_escape(summary)}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
