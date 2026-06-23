from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from voxel_sandbox.app.updates import (
    GitHubRelease,
    ReleaseAsset,
    check_for_update,
    download_release_asset,
    select_platform_asset,
)


class FakeResponse:
    def __init__(self, payload: dict[str, Any] | None = None, chunks: Iterable[bytes] = ()) -> None:
        self._payload = payload or {}
        self._chunks = tuple(chunks)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload

    def iter_content(self, chunk_size: int) -> Iterable[bytes]:
        return self._chunks


class FakeClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[tuple[str, bool]] = []

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        stream: bool = False,
        timeout: float = 10.0,
    ) -> FakeResponse:
        self.requests.append((url, stream))
        return self.response


def test_check_for_update_reads_latest_github_release() -> None:
    client = FakeClient(
        FakeResponse(
            {
                "tag_name": "v0.2.0",
                "name": "Veilstone v0.2.0",
                "html_url": "https://github.com/yarvod/Veilstone/releases/tag/v0.2.0",
                "assets": [
                    {
                        "name": "Veilstone_Windows_x64_v0_2_0.zip",
                        "browser_download_url": "https://example.test/windows.zip",
                        "size": 123,
                    }
                ],
            }
        )
    )

    check = check_for_update(current_version="0.1.0", client=client)

    assert check.update_available is True
    assert check.latest.tag_name == "v0.2.0"
    assert check.latest.assets[0].name == "Veilstone_Windows_x64_v0_2_0.zip"


def test_select_platform_asset_prefers_matching_system_and_arch() -> None:
    release = GitHubRelease(
        tag_name="v0.2.0",
        name="Veilstone v0.2.0",
        html_url="https://example.test/release",
        assets=(
            ReleaseAsset("Veilstone_Linux_x64_v0_2_0.zip", "https://example.test/linux.zip", 1),
            ReleaseAsset("Veilstone_macOS_arm64_v0_2_0.zip", "https://example.test/mac.zip", 1),
        ),
    )

    asset = select_platform_asset(release, system="Darwin", machine="arm64")

    assert asset is not None
    assert asset.name == "Veilstone_macOS_arm64_v0_2_0.zip"


def test_download_release_asset_writes_to_updates_staging(tmp_path: Path) -> None:
    asset = ReleaseAsset(
        name="Veilstone Linux x64.zip",
        browser_download_url="https://example.test/linux.zip",
        size=6,
    )
    client = FakeClient(FakeResponse(chunks=(b"abc", b"def")))

    path = download_release_asset(asset, destination_dir=tmp_path, client=client)

    assert path == tmp_path / "Veilstone_Linux_x64.zip"
    assert path.read_bytes() == b"abcdef"
    assert client.requests == [("https://example.test/linux.zip", True)]
