from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PositionSample:
    timestamp: float
    position: tuple[float, float, float]


class SnapshotInterpolator:
    def __init__(self, delay: float = 0.1, capacity: int = 20) -> None:
        self.delay = delay
        self.samples: deque[PositionSample] = deque(maxlen=capacity)

    def push(self, timestamp: float, position: tuple[float, float, float]) -> None:
        if self.samples and timestamp <= self.samples[-1].timestamp:
            return
        self.samples.append(PositionSample(timestamp, position))

    def sample(self, now: float) -> tuple[float, float, float] | None:
        if not self.samples:
            return None
        target = now - self.delay
        while len(self.samples) >= 2 and self.samples[1].timestamp <= target:
            self.samples.popleft()
        if len(self.samples) == 1 or target <= self.samples[0].timestamp:
            return self.samples[0].position
        first, second = self.samples[0], self.samples[1]
        duration = second.timestamp - first.timestamp
        amount = min(1.0, max(0.0, (target - first.timestamp) / duration))
        return (
            first.position[0] + (second.position[0] - first.position[0]) * amount,
            first.position[1] + (second.position[1] - first.position[1]) * amount,
            first.position[2] + (second.position[2] - first.position[2]) * amount,
        )


def reconcile_position(
    predicted: tuple[float, float, float],
    authoritative: tuple[float, float, float],
    *,
    snap_distance: float = 3.0,
    correction: float = 0.2,
) -> tuple[float, float, float]:
    squared_distance = sum((authoritative[index] - predicted[index]) ** 2 for index in range(3))
    if squared_distance >= snap_distance * snap_distance:
        return authoritative
    return (
        predicted[0] + (authoritative[0] - predicted[0]) * correction,
        predicted[1] + (authoritative[1] - predicted[1]) * correction,
        predicted[2] + (authoritative[2] - predicted[2]) * correction,
    )
