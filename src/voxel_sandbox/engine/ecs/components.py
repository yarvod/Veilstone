from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from voxel_sandbox.domain.items import ItemStack

type EntityId = int


@dataclass(slots=True)
class Transform:
    x: float
    y: float
    z: float
    yaw: float = 0.0

    @property
    def position(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z


@dataclass(slots=True)
class Velocity:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass(frozen=True, slots=True)
class Collider:
    width: float
    height: float


@dataclass(slots=True)
class Health:
    current: float
    maximum: float

    def damage(self, amount: float) -> bool:
        if amount < 0.0:
            raise ValueError("Damage cannot be negative")
        self.current = max(0.0, self.current - amount)
        return self.current == 0.0


@dataclass(frozen=True, slots=True)
class RenderModel:
    key: str
    color: tuple[float, float, float]
    scale: tuple[float, float, float]


class MobKind(Enum):
    PASSIVE = "passive"
    HOSTILE = "hostile"


class MobState(Enum):
    IDLE = "idle"
    WANDER = "wander"
    FLEE = "flee"
    CHASE = "chase"
    ATTACK = "attack"
    HURT = "hurt"
    DEATH = "death"
    GRAZE = "graze"


@dataclass(slots=True)
class AnimationState:
    phase: float = 0.0
    speed: float = 0.0
    state: MobState = MobState.IDLE
    state_phase: float = 0.0
    hurt_remaining: float = 0.0
    death_remaining: float = 0.0


@dataclass(slots=True)
class MobAI:
    kind: MobKind
    state: MobState = MobState.IDLE
    state_time: float = 0.0
    direction_x: float = 0.0
    direction_z: float = 0.0
    attack_cooldown: float = 0.0
    knockback_remaining: float = 0.0


@dataclass(slots=True)
class Lifetime:
    remaining: float


@dataclass(frozen=True, slots=True)
class ItemEntity:
    stack: ItemStack
