from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class TokenBucket:
    rate: float
    capacity: float
    tokens: float = field(init=False)
    updated_at: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        self.tokens = self.capacity

    def allow(self, cost: float = 1.0, *, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        elapsed = max(0.0, current - self.updated_at)
        self.updated_at = current
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens < cost:
            return False
        self.tokens -= cost
        return True
