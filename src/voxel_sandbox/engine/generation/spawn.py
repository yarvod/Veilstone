from __future__ import annotations

from collections.abc import Callable

BlockGetter = Callable[[int, int, int], int]
HeightGetter = Callable[[int, int], int]
SolidPredicate = Callable[[int], bool]


def find_safe_spawn(
    get_block: BlockGetter,
    surface_height: HeightGetter,
    is_solid: SolidPredicate,
    *,
    preferred_x: int = 8,
    preferred_z: int = 8,
    search_radius: int = 7,
) -> tuple[float, float, float]:
    candidates = (
        (x, z)
        for x in range(preferred_x - search_radius, preferred_x + search_radius + 1)
        for z in range(preferred_z - search_radius, preferred_z + search_radius + 1)
    )
    ordered = sorted(
        candidates,
        key=lambda position: (
            (position[0] - preferred_x) ** 2 + (position[1] - preferred_z) ** 2,
            position[1],
            position[0],
        ),
    )
    for x, z in ordered:
        y = surface_height(x, z)
        if not is_solid(get_block(x, y - 1, z)):
            continue
        if is_solid(get_block(x, y, z)) or is_solid(get_block(x, y + 1, z)):
            continue
        return x + 0.5, float(y), z + 0.5
    raise RuntimeError("No safe player spawn found near the preferred position")
