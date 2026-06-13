from __future__ import annotations

import pytest

from voxel_sandbox.__main__ import main

pytestmark = pytest.mark.smoke


@pytest.mark.parametrize(
    "arguments",
    [
        ["--smoke-test"],
        ["server", "--smoke-test"],
    ],
    ids=["primary-player-entry", "dedicated-server"],
)
def test_application_entry_points_start_and_stop(arguments: list[str]) -> None:
    assert main(arguments) == 0
