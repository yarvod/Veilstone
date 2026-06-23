from __future__ import annotations

import platform
import re
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import requests

from voxel_sandbox.app.paths import updates_root
from voxel_sandbox.version import REPO_SLUG, __version__

GITHUB_API_ROOT = "https://api.github.com"


class HttpResponse(Protocol):
    def raise_for_status(self) -> None: ...

    def json(self) -> Any: ...

    def iter_content(self, chunk_size: int) -> Iterable[bytes]: ...


class HttpClient(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        stream: bool = False,
        timeout: float = 10.0,
    ) -> HttpResponse: ...


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    browser_download_url: str
    size: int


@dataclass(frozen=True)
class GitHubRelease:
    tag_name: str
    name: str
    html_url: str
    assets: tuple[ReleaseAsset, ...]
    draft: bool = False
    prerelease: bool = False


@dataclass(frozen=True)
class UpdateCheck:
    current_version: str
    latest: GitHubRelease
    update_available: bool


def fetch_latest_release(
    repo_slug: str = REPO_SLUG,
    *,
    client: HttpClient | None = None,
    timeout: float = 10.0,
) -> GitHubRelease:
    http = client or requests.Session()
    response = http.get(
        f"{GITHUB_API_ROOT}/repos/{repo_slug}/releases/latest",
        headers={"Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = _json_object(response.json())
    return _release_from_payload(payload)


def fetch_releases(
    repo_slug: str = REPO_SLUG,
    *,
    client: HttpClient | None = None,
    timeout: float = 10.0,
    include_prereleases: bool = True,
) -> tuple[GitHubRelease, ...]:
    http = client or requests.Session()
    response = http.get(
        f"{GITHUB_API_ROOT}/repos/{repo_slug}/releases",
        headers={"Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("GitHub releases response must be a JSON array")
    releases: list[GitHubRelease] = []
    for item in cast(list[object], payload):
        if not isinstance(item, Mapping):
            continue
        release = _release_from_payload(cast(Mapping[str, object], item))
        if release.draft:
            continue
        if release.prerelease and not include_prereleases:
            continue
        releases.append(release)
    return tuple(releases)


def check_for_update(
    *,
    current_version: str = __version__,
    repo_slug: str = REPO_SLUG,
    client: HttpClient | None = None,
    timeout: float = 10.0,
) -> UpdateCheck:
    latest = fetch_latest_release(repo_slug, client=client, timeout=timeout)
    return UpdateCheck(
        current_version=current_version,
        latest=latest,
        update_available=_version_key(latest.tag_name) > _version_key(current_version),
    )


def select_platform_asset(
    release: GitHubRelease,
    *,
    system: str | None = None,
    machine: str | None = None,
) -> ReleaseAsset | None:
    system_tokens = _system_tokens(system or platform.system())
    arch_tokens = _arch_tokens(machine or platform.machine())
    fallback: ReleaseAsset | None = None
    for asset in release.assets:
        name = asset.name.lower()
        if not name.endswith(".zip"):
            continue
        if not any(token in name for token in system_tokens):
            continue
        if any(token in name for token in arch_tokens):
            return asset
        fallback = fallback or asset
    return fallback


def download_release_asset(
    asset: ReleaseAsset,
    *,
    destination_dir: Path | None = None,
    client: HttpClient | None = None,
    timeout: float = 60.0,
    progress_callback: Callable[[int, int | None], None] | None = None,
) -> Path:
    target_dir = destination_dir or updates_root()
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_asset_name(asset.name)
    target = target_dir / safe_name
    http = client or requests.Session()
    response = http.get(asset.browser_download_url, stream=True, timeout=timeout)
    response.raise_for_status()
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=target_dir, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            received = 0
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    temp_file.write(chunk)
                    received += len(chunk)
                    if progress_callback is not None:
                        progress_callback(received, asset.size or None)
        temp_path.replace(target)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
    return target


def run_check_update(
    *,
    repo_slug: str = REPO_SLUG,
    printer: Callable[[str], None] = print,
) -> int:
    check = check_for_update(repo_slug=repo_slug)
    latest = check.latest
    if check.update_available:
        printer(
            f"Update available: {check.current_version} -> {latest.tag_name} ({latest.html_url})"
        )
        asset = select_platform_asset(latest)
        if asset is not None:
            printer(f"Platform asset: {asset.name}")
        return 0
    printer(f"Veilstone is up to date: {check.current_version} ({latest.tag_name})")
    return 0


def run_download_update(
    *,
    repo_slug: str = REPO_SLUG,
    destination_dir: Path | None = None,
    printer: Callable[[str], None] = print,
) -> int:
    check = check_for_update(repo_slug=repo_slug)
    asset = select_platform_asset(check.latest)
    if asset is None:
        printer(f"No zip asset for this platform in {check.latest.tag_name}")
        return 1
    path = download_release_asset(asset, destination_dir=destination_dir)
    printer(f"Downloaded {asset.name} to {path}")
    return 0


def _version_key(value: str) -> tuple[int, ...]:
    text = value.strip().removeprefix("v")
    parts = re.split(r"[^0-9]+", text)
    numbers = tuple(int(part) for part in parts if part)
    return numbers or (0,)


def _system_tokens(system: str) -> tuple[str, ...]:
    normalized = system.lower()
    if normalized == "darwin":
        return ("macos", "darwin", "mac")
    if normalized == "windows":
        return ("windows", "win")
    if normalized == "linux":
        return ("linux",)
    return (normalized,)


def _arch_tokens(machine: str) -> tuple[str, ...]:
    normalized = machine.lower()
    if normalized in {"x86_64", "amd64"}:
        return ("x64", "x86_64", "amd64")
    if normalized in {"arm64", "aarch64"}:
        return ("arm64", "aarch64")
    if normalized in {"i386", "i686", "x86"}:
        return ("x86", "i386", "i686")
    return (normalized,)


def _safe_asset_name(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    return sanitized or "veilstone-update.zip"


def _json_object(value: Any) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("GitHub release response must be a JSON object")
    return cast(Mapping[str, object], value)


def _release_from_payload(payload: Mapping[str, object]) -> GitHubRelease:
    tag_name = str(payload.get("tag_name") or "")
    return GitHubRelease(
        tag_name=tag_name,
        name=str(payload.get("name") or tag_name),
        html_url=str(payload.get("html_url", "")),
        assets=tuple(_release_assets(payload.get("assets", ()))),
        draft=bool(payload.get("draft", False)),
        prerelease=bool(payload.get("prerelease", False)),
    )


def _release_assets(value: object) -> Iterable[ReleaseAsset]:
    if not isinstance(value, list):
        return ()
    assets: list[ReleaseAsset] = []
    items = cast(list[object], value)
    for item in items:
        if not isinstance(item, Mapping):
            continue
        asset = cast(Mapping[str, object], item)
        download_url = asset.get("browser_download_url")
        if not download_url:
            continue
        size_value = asset.get("size", 0)
        assets.append(
            ReleaseAsset(
                name=str(asset.get("name") or ""),
                browser_download_url=str(download_url),
                size=size_value if isinstance(size_value, int) else 0,
            )
        )
    return assets
