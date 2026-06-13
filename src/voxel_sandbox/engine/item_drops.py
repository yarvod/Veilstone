from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemRegistry, ItemStack


@dataclass(frozen=True, slots=True)
class WorldItemDrop:
    id: int
    position: tuple[float, float, float]
    stack: ItemStack


class ItemDropStore:
    def __init__(self) -> None:
        self._next_id = 1
        self._drops: dict[int, WorldItemDrop] = {}

    def __len__(self) -> int:
        return len(self._drops)

    def all(self) -> tuple[WorldItemDrop, ...]:
        return tuple(self._drops.values())

    def spawn(self, position: tuple[float, float, float], stack: ItemStack) -> WorldItemDrop:
        drop = WorldItemDrop(self._next_id, position, stack)
        self._next_id += 1
        self._drops[drop.id] = drop
        return drop

    def pickup_near(
        self,
        position: tuple[float, float, float],
        radius: float,
        inventory: Inventory,
        registry: ItemRegistry,
    ) -> tuple[ItemStack, ...]:
        radius_squared = radius * radius
        picked_up: list[ItemStack] = []
        for drop_id, drop in tuple(self._drops.items()):
            distance_squared = sum(
                (drop.position[index] - position[index]) ** 2 for index in range(3)
            )
            if distance_squared > radius_squared:
                continue
            remainder = inventory.add(drop.stack, registry)
            accepted = drop.stack.count - (remainder.count if remainder else 0)
            if accepted:
                picked_up.append(drop.stack.with_count(accepted))
            if remainder is None:
                del self._drops[drop_id]
            else:
                self._drops[drop_id] = WorldItemDrop(drop.id, drop.position, remainder)
        return tuple(picked_up)
