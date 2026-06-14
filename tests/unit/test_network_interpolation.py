from __future__ import annotations

from voxel_sandbox.network.interpolation import SnapshotInterpolator, reconcile_position


def test_snapshot_interpolator_blends_delayed_positions() -> None:
    interpolation = SnapshotInterpolator(delay=0.1)
    interpolation.push(1.0, (0.0, 0.0, 0.0))
    interpolation.push(1.2, (2.0, 0.0, 0.0))

    position = interpolation.sample(1.2)
    assert position is not None
    assert abs(position[0] - 1.0) < 1e-9


def test_reconciliation_smooths_small_error_and_snaps_large_error() -> None:
    assert reconcile_position((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)) == (0.2, 0.0, 0.0)
    assert reconcile_position((0.0, 0.0, 0.0), (4.0, 0.0, 0.0)) == (4.0, 0.0, 0.0)
