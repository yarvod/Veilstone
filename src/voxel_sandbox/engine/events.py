from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

type GameEvent = (
    BlockInteractionStarted
    | BlockBroken
    | BlockPlaced
    | EntityDamaged
    | EntityDied
    | PlayerLanded
    | PlayerSwimStroke
    | PlayerWaterTransition
)
type EventHandler[T: GameEvent] = Callable[[T], None]


@dataclass(frozen=True, slots=True)
class BlockInteractionStarted:
    action: str
    block_id: int
    position: tuple[int, int, int]
    target_position: tuple[int, int, int]
    normal: tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class BlockBroken:
    block_id: int
    position: tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class BlockPlaced:
    block_id: int
    position: tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class EntityDamaged:
    entity_id: int
    kind: str
    position: tuple[float, float, float]
    amount: float


@dataclass(frozen=True, slots=True)
class EntityDied:
    entity_id: int
    kind: str
    position: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class PlayerLanded:
    position: tuple[float, float, float]
    vertical_velocity: float


@dataclass(frozen=True, slots=True)
class PlayerSwimStroke:
    position: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class PlayerWaterTransition:
    position: tuple[float, float, float]
    entered: bool


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[GameEvent], list[Callable[[GameEvent], None]]] = defaultdict(list)

    def subscribe[T: GameEvent](
        self,
        event_type: type[T],
        handler: EventHandler[T],
    ) -> None:
        self._handlers[event_type].append(cast(Callable[[GameEvent], None], handler))

    def publish(self, event: GameEvent) -> None:
        for handler in tuple(self._handlers[type(event)]):
            handler(event)
