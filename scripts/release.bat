@echo off
setlocal enabledelayedexpansion

set "TAG="
set "REPLACE_TAG=0"

:parse_args
if "%~1"=="" goto args_done
if "%~1"=="-t" (
  if "%~2"=="" goto usage_error
  set "TAG=%~2"
  shift
  shift
  goto parse_args
)
if "%~1"=="--tag" (
  if "%~2"=="" goto usage_error
  set "TAG=%~2"
  shift
  shift
  goto parse_args
)
if "%~1"=="--replace-tag" (
  set "REPLACE_TAG=1"
  shift
  goto parse_args
)
if "%~1"=="--retag" (
  set "REPLACE_TAG=1"
  shift
  goto parse_args
)
if "%~1"=="-h" goto usage_ok
if "%~1"=="--help" goto usage_ok
if not "%TAG%"=="" goto usage_error
set "TAG=%~1"
shift
goto parse_args

:usage_ok
call :print_usage
exit /b 0

:usage_error
call :print_usage
exit /b 2

:print_usage
echo Usage: scripts\release.bat v0.2.0
echo        scripts\release.bat -t v0.2.0
echo        scripts\release.bat -t v0.2.0 --replace-tag
echo        scripts\release.bat -t v0.2.0 --retag
exit /b 0

:args_done
if "%TAG%"=="" goto usage_error

for /f %%i in ('git status --short') do (
  echo Working tree is not clean. Commit or stash changes before releasing.
  exit /b 1
)

if "%REPLACE_TAG%"=="1" (
  uv run python scripts\set_release_version.py --check-current "%TAG%" || exit /b 1
  set "REMOTE_TAG_SHA="
  for /f "tokens=1" %%i in ('git ls-remote --exit-code --refs origin "refs/tags/%TAG%"') do set "REMOTE_TAG_SHA=%%i"
  if "!REMOTE_TAG_SHA!"=="" (
    echo Remote tag %TAG% does not exist. Use normal release mode for a new tag.
    exit /b 1
  )
  git push origin HEAD || exit /b 1
  git tag -f -a "%TAG%" -m "Veilstone %TAG%" || exit /b 1
  git push --force-with-lease="refs/tags/%TAG%:!REMOTE_TAG_SHA!" origin "refs/tags/%TAG%" || exit /b 1
  exit /b 0
)

uv run python scripts\set_release_version.py "%TAG%" || exit /b 1
uv lock || exit /b 1

git add pyproject.toml uv.lock src\voxel_sandbox\version.py || exit /b 1
git commit -m "chore: release %TAG%" || exit /b 1
git tag -a "%TAG%" -m "Veilstone %TAG%" || exit /b 1
git push origin HEAD || exit /b 1
git push origin "%TAG%" || exit /b 1

endlocal
