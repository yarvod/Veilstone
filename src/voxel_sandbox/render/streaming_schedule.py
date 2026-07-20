from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Protocol

from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, SECTION_SIZE


class BoundsVisibility(Protocol):
    def intersects(
        self,
        minimum: tuple[float, float, float],
        maximum: tuple[float, float, float],
    ) -> bool: ...


def frame_budget(value: int) -> int:
    return max(0, value)


def drain_fifo_keys[TKey](queue: MutableMapping[TKey, None], budget: int) -> tuple[TKey, ...]:
    selected = tuple(queue)[: frame_budget(budget)]
    for key in selected:
        queue.pop(key, None)
    return selected


def drain_priority_keys[TKey, TPriority](
    queue: MutableMapping[TKey, None],
    budget: int,
    priority: Callable[[TKey], TPriority],
) -> tuple[TKey, ...]:
    limit = frame_budget(budget)
    if limit == 0:
        return ()
    ranked = sorted(enumerate(queue), key=lambda entry: (priority(entry[1]), entry[0]))
    selected = tuple(key for _index, key in ranked[:limit])
    for key in selected:
        queue.pop(key, None)
    return selected


def drain_grouped_priority_keys[TKey, TPrimary, TSecondary](
    queue: MutableMapping[TKey, None],
    budget: int,
    primary: Callable[[TKey], TPrimary],
    secondary: Callable[[TKey], TSecondary],
) -> tuple[TKey, ...]:
    """Rank all work by cheap primary priority and score only the cutoff group."""
    limit = min(frame_budget(budget), len(queue))
    if limit == 0:
        return ()

    ranked_primary = [(primary(key), index, key) for index, key in enumerate(queue)]
    ranked_primary.sort(key=lambda entry: (entry[0], entry[1]))
    cutoff = ranked_primary[limit - 1][0]
    candidate_count = limit
    while candidate_count < len(ranked_primary) and ranked_primary[candidate_count][0] == cutoff:
        candidate_count += 1
    candidates = ranked_primary[:candidate_count]
    candidates.sort(key=lambda entry: (entry[0], secondary(entry[2]), entry[1]))
    selected = tuple(key for _primary, _index, key in candidates[:limit])
    for key in selected:
        queue.pop(key, None)
    return selected


def chunk_distance(left: tuple[int, int], right: tuple[int, int]) -> int:
    return max(abs(left[0] - right[0]), abs(left[1] - right[1]))


def streaming_priority(
    distance: int,
    visible: bool | None,
    collision_critical: bool | None = None,
) -> tuple[int, int, int]:
    return distance, int(collision_critical is not True), int(visible is False)


def chunk_visible(
    view: BoundsVisibility | None,
    coord: tuple[int, int],
) -> bool | None:
    if view is None:
        return None
    x, z = coord
    return view.intersects(
        (float(x * SECTION_SIZE), 0.0, float(z * SECTION_SIZE)),
        (float((x + 1) * SECTION_SIZE), float(CHUNK_HEIGHT), float((z + 1) * SECTION_SIZE)),
    )


def section_visible(
    view: BoundsVisibility | None,
    coord: tuple[int, int, int],
) -> bool | None:
    if view is None:
        return None
    x, y, z = coord
    return view.intersects(
        (float(x * SECTION_SIZE), float(y * SECTION_SIZE), float(z * SECTION_SIZE)),
        (
            float((x + 1) * SECTION_SIZE),
            float((y + 1) * SECTION_SIZE),
            float((z + 1) * SECTION_SIZE),
        ),
    )
