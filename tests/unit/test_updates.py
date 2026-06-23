from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from voxel_sandbox.app.updates import (
    GitHubRelease,
    ReleaseAsset,
    check_for_update,
    download_release_asset,
    fetch_releases,
    select_platform_asset,
)


class FakeResponse:
    def __init__(self, payload: object | None = None, chunks: Iterable[bytes] = ()) -> None:
        self._payload: object = {} if payload is None else payload
        self._chunks = tuple(chunks)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
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


def test_fetch_releases_filters_drafts_and_keeps_prereleases_by_default() -> None:
    payload: list[object] = [
        {
            "tag_name": "v0.3.0",
            "name": "Veilstone v0.3.0",
            "html_url": "https://example.test/v0.3.0",
            "assets": [],
            "draft": False,
            "prerelease": True,
        },
        {
            "tag_name": "v0.2.0",
            "name": "Veilstone v0.2.0",
            "html_url": "https://example.test/v0.2.0",
            "assets": [
                {
                    "name": "Veilstone_Linux_x64_v0_2_0.zip",
                    "browser_download_url": "https://example.test/linux.zip",
                    "size": 123,
                }
            ],
            "draft": False,
            "prerelease": False,
        },
        {
            "tag_name": "v0.1.0",
            "name": "Draft",
            "html_url": "https://example.test/draft",
            "assets": [],
            "draft": True,
            "prerelease": False,
        },
    ]
    client = FakeClient(FakeResponse(payload))

    releases = fetch_releases(client=client)

    assert [release.tag_name for release in releases] == ["v0.3.0", "v0.2.0"]
    assert releases[0].prerelease is True
    assert releases[1].assets[0].name == "Veilstone_Linux_x64_v0_2_0.zip"
    assert client.requests == [("https://api.github.com/repos/yarvod/Veilstone/releases", False)]


def test_fetch_releases_can_hide_prereleases() -> None:
    payload: list[object] = [
        {"tag_name": "v0.3.0", "draft": False, "prerelease": True},
        {"tag_name": "v0.2.0", "draft": False, "prerelease": False},
    ]
    client = FakeClient(FakeResponse(payload))

    releases = fetch_releases(client=client, include_prereleases=False)

    assert [release.tag_name for release in releases] == ["v0.2.0"]
