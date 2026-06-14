from __future__ import annotations

import pytest

from voxel_sandbox.tools.structure_preview import run_preview


def test_structure_preview_prints_layers_and_loot(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_preview("veilstone_ruin") == 0
    output = capsys.readouterr().out

    assert "veilstone_ruin size=(5, 5, 5)" in output
    assert "layer y=3" in output
    assert "loot item=6" in output
