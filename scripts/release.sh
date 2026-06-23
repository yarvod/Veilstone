#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: scripts/release.sh v0.2.0"
  echo "       scripts/release.sh -t v0.2.0"
  echo "       scripts/release.sh -t v0.2.0 --replace-tag"
  echo "       scripts/release.sh -t v0.2.0 --retag"
}

TAG=""
REPLACE_TAG=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--tag)
      if [[ $# -lt 2 ]]; then
        usage
        exit 2
      fi
      TAG="$2"
      shift 2
      ;;
    --replace-tag|--retag)
      REPLACE_TAG=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      usage
      exit 2
      ;;
    *)
      if [[ -n "$TAG" ]]; then
        usage
        exit 2
      fi
      TAG="$1"
      shift
      ;;
  esac
done

if [[ -z "$TAG" ]]; then
  usage
  exit 2
fi

if [[ -n "$(git status --short)" ]]; then
  echo "Working tree is not clean. Commit or stash changes before releasing."
  exit 1
fi

if [[ "$REPLACE_TAG" -eq 1 ]]; then
  uv run python scripts/set_release_version.py --check-current "$TAG"
  REMOTE_TAG_SHA="$(git ls-remote --exit-code --refs origin "refs/tags/$TAG" | awk '{print $1}')"
  if [[ -z "$REMOTE_TAG_SHA" ]]; then
    echo "Remote tag $TAG does not exist. Use normal release mode for a new tag."
    exit 1
  fi
  git push origin HEAD
  git tag -f -a "$TAG" -m "Veilstone $TAG"
  git push --force-with-lease="refs/tags/$TAG:$REMOTE_TAG_SHA" origin "refs/tags/$TAG"
  exit 0
fi

uv run python scripts/set_release_version.py "$TAG"
uv lock

git add pyproject.toml uv.lock src/voxel_sandbox/version.py
git commit -m "chore: release $TAG"
git tag -a "$TAG" -m "Veilstone $TAG"
git push origin HEAD
git push origin "$TAG"
