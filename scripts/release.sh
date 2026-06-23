#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: scripts/release.sh v0.2.0"
  echo "       scripts/release.sh -t v0.2.0"
}

TAG=""
while getopts "t:h" opt; do
  case "$opt" in
    t) TAG="$OPTARG" ;;
    h) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

if [[ -z "$TAG" && $# -gt 0 ]]; then
  TAG="$1"
fi
if [[ -z "$TAG" ]]; then
  usage
  exit 2
fi

if [[ -n "$(git status --short)" ]]; then
  echo "Working tree is not clean. Commit or stash changes before releasing."
  exit 1
fi

uv run python scripts/set_release_version.py "$TAG"
uv lock

git add pyproject.toml uv.lock src/voxel_sandbox/version.py
git commit -m "chore: release $TAG"
git tag -a "$TAG" -m "Veilstone $TAG"
git push origin HEAD
git push origin "$TAG"
