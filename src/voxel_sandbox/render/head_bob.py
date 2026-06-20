from __future__ import annotations

import math
from dataclasses import dataclass, field

_BOB_AMPLITUDE: float = 0.04
_BOB_SPEED: float = 11.0
_BOB_BLEND_SPEED: float = 10.0


@dataclass(slots=True)
class HeadBob:
    _phase: float = field(default=0.0, init=False)
    _amplitude: float = field(default=0.0, init=False)

    @property
    def offset_y(self) -> float:
        return math.sin(self._phase) * self._amplitude

    def update(self, moving: bool, on_ground: bool, delta_time: float) -> None:
        target = _BOB_AMPLITUDE if (moving and on_ground) else 0.0
        self._amplitude += (target - self._amplitude) * min(1.0, _BOB_BLEND_SPEED * delta_time)
        self._phase += _BOB_SPEED * delta_time
