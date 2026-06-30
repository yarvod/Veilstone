from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.domain.crafting import CraftingGrid
from voxel_sandbox.domain.items import ItemRegistry, ItemStack


@dataclass(frozen=True, slots=True)
class ItemIconSnapshot:
    item_id: int
    count: int
    name: str
    count_text: str
    tooltip: str
    model_key: str


@dataclass(frozen=True, slots=True)
class CraftingResultSnapshot:
    result: ItemIconSnapshot | None
    has_inputs: bool
    status_text: str

    @property
    def available(self) -> bool:
        return self.result is not None


def build_item_icon_snapshot(
    stack: ItemStack,
    item_registry: ItemRegistry,
) -> ItemIconSnapshot:
    definition = item_registry.by_id(stack.item_id)
    count_text = str(stack.count) if stack.count > 1 else ""
    tooltip = definition.name if stack.count == 1 else f"{definition.name} x{stack.count}"
    return ItemIconSnapshot(
        item_id=stack.item_id,
        count=stack.count,
        name=definition.name,
        count_text=count_text,
        tooltip=tooltip,
        model_key=definition.key,
    )


def build_crafting_result_snapshot(
    result: ItemStack | None,
    crafting_grid: CraftingGrid,
    item_registry: ItemRegistry,
) -> CraftingResultSnapshot:
    has_inputs = any(crafting_grid[index] is not None for index in range(len(crafting_grid)))
    item = build_item_icon_snapshot(result, item_registry) if result is not None else None
    status_text = "" if item is not None or not has_inputs else "No matching recipe"
    return CraftingResultSnapshot(result=item, has_inputs=has_inputs, status_text=status_text)
