from __future__ import annotations

import numpy as np

from voxel_sandbox.engine.perf.greedy_rectangles import (
    NATIVE_GREEDY_RECTANGLES,
    greedy_rectangles,
    python_greedy_rectangles,
)


def _fixture() -> tuple[np.ndarray, np.ndarray]:
    signatures = np.array(
        [
            [0, 0, 1, -1, 2, 2],
            [0, 0, 1, -1, 2, 2],
            [3, 3, 1, 4, 4, 2],
            [3, 3, -1, 4, 4, 2],
        ],
        dtype=np.int32,
    )
    faces = np.arange(signatures.size, dtype=np.int32).reshape(signatures.shape)
    return signatures, faces


def test_selected_greedy_scanner_matches_python_reference() -> None:
    signatures, faces = _fixture()
    expected_signatures = signatures.copy()
    actual_signatures = signatures.copy()

    expected = python_greedy_rectangles(expected_signatures, faces)
    actual = greedy_rectangles(actual_signatures, faces)

    assert actual == expected
    np.testing.assert_array_equal(actual_signatures, expected_signatures)
    np.testing.assert_array_equal(faces, _fixture()[1])


def test_python_fallback_reports_native_state_consistently() -> None:
    assert NATIVE_GREEDY_RECTANGLES is (greedy_rectangles is not python_greedy_rectangles)
