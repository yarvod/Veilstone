from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

BlockGetter = Callable[[int, int, int], int]


@dataclass(frozen=True, slots=True)
class RaycastHit:
    block: tuple[int, int, int]
    previous: tuple[int, int, int]
    normal: tuple[int, int, int]
    distance: float
    block_id: int


def voxel_raycast(
    get_block: BlockGetter,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    max_distance: float,
    skip_block: Callable[[int], bool] | None = None,
) -> RaycastHit | None:
    length = math.sqrt(sum(component * component for component in direction))
    if length == 0.0 or max_distance < 0.0:
        return None
    ray = tuple(component / length for component in direction)
    voxel = [math.floor(component) for component in origin]
    previous = _tuple3(voxel)
    block_id = get_block(*voxel)
    if block_id != 0 and not (skip_block and skip_block(block_id)):
        return RaycastHit(_tuple3(voxel), previous, (0, 0, 0), 0.0, block_id)

    step = [1 if component > 0.0 else -1 if component < 0.0 else 0 for component in ray]
    delta = [abs(1.0 / component) if component != 0.0 else math.inf for component in ray]
    side = [
        ((voxel[axis] + 1 - origin[axis]) if step[axis] > 0 else (origin[axis] - voxel[axis]))
        * delta[axis]
        if step[axis] != 0
        else math.inf
        for axis in range(3)
    ]

    distance = 0.0
    while distance <= max_distance:
        axis = min(range(3), key=side.__getitem__)
        distance = side[axis]
        if distance > max_distance:
            break
        previous = _tuple3(voxel)
        voxel[axis] += step[axis]
        side[axis] += delta[axis]
        block_id = get_block(*voxel)
        if block_id != 0 and not (skip_block and skip_block(block_id)):
            normal = [0, 0, 0]
            normal[axis] = -step[axis]
            return RaycastHit(_tuple3(voxel), previous, _tuple3(normal), distance, block_id)
    return None


def _tuple3(values: list[int]) -> tuple[int, int, int]:
    return values[0], values[1], values[2]
