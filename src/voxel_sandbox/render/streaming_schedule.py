from __future__ import annotations

from collections.abc import Callable, MutableMapping


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


def chunk_distance(left: tuple[int, int], right: tuple[int, int]) -> int:
    return max(abs(left[0] - right[0]), abs(left[1] - right[1]))
