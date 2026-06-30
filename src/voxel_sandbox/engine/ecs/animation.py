from __future__ import annotations

import math


def mob_locomotion_cycle(phase: float, speed: float) -> float:
    return phase * (2.2 + speed * 1.2)


def mob_step_index(phase: float, speed: float) -> int:
    if speed <= 0.05:
        return 0
    return max(0, math.floor(mob_locomotion_cycle(phase, speed) / math.pi))
