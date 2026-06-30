from __future__ import annotations

from collections.abc import MutableMapping


def frame_budget(value: int) -> int:
    return max(0, value)


def drain_fifo_keys[TKey](queue: MutableMapping[TKey, None], budget: int) -> tuple[TKey, ...]:
    selected = tuple(queue)[: frame_budget(budget)]
    for key in selected:
        queue.pop(key, None)
    return selected
