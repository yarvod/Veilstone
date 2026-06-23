@echo off
setlocal enabledelayedexpansion

set "TAG="
if "%~1"=="-t" (
    set "TAG=%~2"
) else (
    set "TAG=%~1"
)

if "%TAG%"=="" (
    echo Usage: scripts\release.bat v0.2.0
    echo        scripts\release.bat -t v0.2.0
    exit /b 2
)

for /f %%i in ('git status --short') do (
    echo Working tree is not clean. Commit or stash changes before releasing.
    exit /b 1
)

uv run python scripts\set_release_version.py "%TAG%" || exit /b 1
uv lock || exit /b 1

git add pyproject.toml uv.lock src\voxel_sandbox\version.py || exit /b 1
git commit -m "chore: release %TAG%" || exit /b 1
git tag -a "%TAG%" -m "Veilstone %TAG%" || exit /b 1
git push origin HEAD || exit /b 1
git push origin "%TAG%" || exit /b 1

endlocal
