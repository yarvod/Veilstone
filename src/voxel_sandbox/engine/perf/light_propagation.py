from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

LightPropagator = Callable[[NDArray[np.uint8], NDArray[np.bool_]], NDArray[np.uint8]]


def python_propagate_light(
    sources: NDArray[np.uint8],
    opaque: NDArray[np.bool_],
) -> NDArray[np.uint8]:
    light = sources.copy()
    if not np.any(light):
        return light
    blocked = opaque & (sources == 0)
    attenuated = np.empty_like(light)
    neighbors = np.empty_like(light)
    updated = np.empty_like(light)
    for _ in range(15):
        np.maximum(light, 1, out=attenuated)
        np.subtract(attenuated, 1, out=attenuated)
        neighbors.fill(0)
        np.maximum(neighbors[1:, :, :], attenuated[:-1, :, :], out=neighbors[1:, :, :])
        np.maximum(neighbors[:-1, :, :], attenuated[1:, :, :], out=neighbors[:-1, :, :])
        np.maximum(neighbors[:, 1:, :], attenuated[:, :-1, :], out=neighbors[:, 1:, :])
        np.maximum(neighbors[:, :-1, :], attenuated[:, 1:, :], out=neighbors[:, :-1, :])
        np.maximum(neighbors[:, :, 1:], attenuated[:, :, :-1], out=neighbors[:, :, 1:])
        np.maximum(neighbors[:, :, :-1], attenuated[:, :, 1:], out=neighbors[:, :, :-1])
        np.maximum(sources, neighbors, out=updated)
        updated[blocked] = 0
        if np.array_equal(updated, light):
            break
        light, updated = updated, light
    return light


try:
    from voxel_sandbox.engine.perf.cy_light import propagate_light as _cython_propagate_light
except ImportError:
    _cython_propagate_light = None


def _native_propagate_light(
    sources: NDArray[np.uint8],
    opaque: NDArray[np.bool_],
) -> NDArray[np.uint8]:
    assert _cython_propagate_light is not None
    return _cython_propagate_light(sources, opaque.view(np.uint8))


NATIVE_LIGHT_PROPAGATION = _cython_propagate_light is not None


def propagate_light(
    sources: NDArray[np.uint8],
    opaque: NDArray[np.bool_],
) -> NDArray[np.uint8]:
    source_count = int(np.count_nonzero(sources))
    if source_count == 0:
        return sources.copy()
    if NATIVE_LIGHT_PROPAGATION and source_count <= sources.size // 8:
        return _native_propagate_light(sources, opaque)
    return python_propagate_light(sources, opaque)
