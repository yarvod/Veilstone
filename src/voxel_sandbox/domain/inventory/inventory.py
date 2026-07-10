from __future__ import annotations

from collections.abc import Iterator

from voxel_sandbox.domain.items import ItemRegistry, ItemStack


class Inventory:
    def __init__(self, width: int = 9, height: int = 4) -> None:
        if width < 1 or height < 1:
            raise ValueError("Inventory dimensions must be positive")
        self.width = width
        self.height = height
        self._slots: list[ItemStack | None] = [None] * (width * height)

    def __len__(self) -> int:
        return len(self._slots)

    def __iter__(self) -> Iterator[ItemStack | None]:
        return iter(self._slots)

    def __getitem__(self, index: int) -> ItemStack | None:
        return self._slots[index]

    def set(self, index: int, stack: ItemStack | None, registry: ItemRegistry) -> None:
        self._validate_index(index)
        if stack is not None and stack.count > registry.by_id(stack.item_id).max_stack:
            raise ValueError("Stack exceeds the item's maximum size")
        self._slots[index] = stack

    def add(self, stack: ItemStack, registry: ItemRegistry) -> ItemStack | None:
        maximum = registry.by_id(stack.item_id).max_stack
        remaining = stack.count
        for index, current in enumerate(self._slots):
            if current is None or current.item_id != stack.item_id or current.count >= maximum:
                continue
            moved = min(maximum - current.count, remaining)
            self._slots[index] = current.with_count(current.count + moved)
            remaining -= moved
            if remaining == 0:
                return None
        for index, current in enumerate(self._slots):
            if current is not None:
                continue
            moved = min(maximum, remaining)
            self._slots[index] = stack.with_count(moved)
            remaining -= moved
            if remaining == 0:
                return None
        return stack.with_count(remaining)

    def remove(self, item_id: int, count: int) -> bool:
        if count < 1:
            raise ValueError("Removal count must be positive")
        if self.count(item_id) < count:
            return False
        remaining = count
        for index, current in enumerate(self._slots):
            if current is None or current.item_id != item_id:
                continue
            removed = min(current.count, remaining)
            new_count = current.count - removed
            self._slots[index] = current.with_count(new_count) if new_count else None
            remaining -= removed
            if remaining == 0:
                return True
        return True

    def take_from_slot(self, index: int, count: int = 1) -> ItemStack | None:
        self._validate_index(index)
        if count < 1:
            raise ValueError("Take count must be positive")
        current = self._slots[index]
        if current is None:
            return None
        taken = min(count, current.count)
        remaining = current.count - taken
        self._slots[index] = current.with_count(remaining) if remaining else None
        return current.with_count(taken)

    def split(self, index: int) -> ItemStack | None:
        current = self[index]
        if current is None:
            return None
        return self.take_from_slot(index, (current.count + 1) // 2)

    def move(self, source: int, target: int, registry: ItemRegistry) -> None:
        self._validate_index(source)
        self._validate_index(target)
        if source == target:
            return
        first, second = self._slots[source], self._slots[target]
        if first is None:
            return
        if second is None or second.item_id != first.item_id:
            self._slots[source], self._slots[target] = second, first
            return
        maximum = registry.by_id(first.item_id).max_stack
        moved = min(maximum - second.count, first.count)
        self._slots[target] = second.with_count(second.count + moved)
        remaining = first.count - moved
        self._slots[source] = first.with_count(remaining) if remaining else None

    def count(self, item_id: int) -> int:
        return sum(stack.count for stack in self._slots if stack and stack.item_id == item_id)

    def clone(self) -> Inventory:
        copy = Inventory(self.width, self.height)
        copy._slots = list(self._slots)
        return copy

    def replace_from(self, other: Inventory) -> None:
        if (self.width, self.height) != (other.width, other.height):
            raise ValueError("Inventory dimensions must match")
        self._slots = list(other._slots)

    def _validate_index(self, index: int) -> None:
        if not 0 <= index < len(self._slots):
            raise IndexError(f"Inventory slot out of range: {index}")


class Hotbar:
    SLOT_COUNT = 9

    def __init__(self, inventory: Inventory) -> None:
        if inventory.width < self.SLOT_COUNT:
            raise ValueError("Inventory must expose at least nine hotbar slots")
        self.inventory = inventory
        self.selected_index = 0

    @property
    def selected(self) -> ItemStack | None:
        return self.inventory[self.selected_index]

    def select(self, index: int) -> None:
        if not 0 <= index < self.SLOT_COUNT:
            raise IndexError(f"Hotbar slot out of range: {index}")
        self.selected_index = index

    def cycle(self, delta: int) -> None:
        self.selected_index = (self.selected_index + delta) % self.SLOT_COUNT
