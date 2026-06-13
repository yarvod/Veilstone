from __future__ import annotations

import tomllib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TypeIs, cast

from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemRegistry, ItemStack


@dataclass(frozen=True, slots=True)
class Recipe:
    key: str
    pattern: tuple[tuple[int | None, ...], ...]
    result: ItemStack
    shaped: bool

    @property
    def width(self) -> int:
        return len(self.pattern[0]) if self.pattern else 0

    @property
    def height(self) -> int:
        return len(self.pattern)

    @property
    def required_items(self) -> Counter[int]:
        return Counter(item_id for row in self.pattern for item_id in row if item_id is not None)


class CraftingGrid:
    def __init__(self, width: int, height: int) -> None:
        if width not in {2, 3} or height not in {2, 3}:
            raise ValueError("Crafting grids must be 2x2 or 3x3")
        self.width = width
        self.height = height
        self._slots: list[ItemStack | None] = [None] * (width * height)

    def __getitem__(self, index: int) -> ItemStack | None:
        return self._slots[index]

    def set(self, x: int, y: int, stack: ItemStack | None) -> None:
        self._slots[self._index(x, y)] = stack

    def pattern(self) -> tuple[tuple[int | None, ...], ...]:
        rows: list[tuple[int | None, ...]] = []
        for y in range(self.height):
            row: list[int | None] = []
            for x in range(self.width):
                stack = self._slots[self._index(x, y)]
                row.append(stack.item_id if stack is not None else None)
            rows.append(tuple(row))
        return _trim_pattern(tuple(rows))

    def consume_one(self) -> None:
        for index, stack in enumerate(self._slots):
            if stack is None:
                continue
            self._slots[index] = stack.with_count(stack.count - 1) if stack.count > 1 else None

    def _index(self, x: int, y: int) -> int:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"Crafting slot out of range: {(x, y)}")
        return y * self.width + x


class RecipeBook:
    def __init__(self, recipes: tuple[Recipe, ...]) -> None:
        if len({recipe.key for recipe in recipes}) != len(recipes):
            raise ValueError("Recipe keys must be unique")
        self.recipes = recipes
        self._by_key = {recipe.key: recipe for recipe in recipes}

    @classmethod
    def from_toml(cls, path: Path, registry: ItemRegistry) -> RecipeBook:
        with path.open("rb") as file:
            payload = cast(dict[str, object], tomllib.load(file))
        raw_recipes = payload.get("recipes", [])
        if not isinstance(raw_recipes, list):
            raise ValueError("recipes.toml must contain [[recipes]] entries")
        recipes: list[Recipe] = []
        for raw in cast(list[object], raw_recipes):
            if not isinstance(raw, dict):
                raise ValueError("Each recipe must be a TOML table")
            recipes.append(_parse_recipe(cast(dict[str, object], raw), registry))
        return cls(tuple(recipes))

    def by_key(self, key: str) -> Recipe:
        try:
            return self._by_key[key]
        except KeyError as error:
            raise KeyError(f"Unknown recipe: {key}") from error

    def match(self, grid: CraftingGrid) -> Recipe | None:
        pattern = grid.pattern()
        flat = Counter(item_id for row in pattern for item_id in row if item_id is not None)
        for recipe in self.recipes:
            if not _fits_grid(recipe, grid.width, grid.height):
                continue
            if recipe.shaped and recipe.pattern == pattern:
                return recipe
            if not recipe.shaped and recipe.required_items == flat:
                return recipe
        return None

    def craft(self, grid: CraftingGrid) -> ItemStack | None:
        recipe = self.match(grid)
        if recipe is None:
            return None
        grid.consume_one()
        return recipe.result

    def craft_from_inventory(
        self,
        key: str,
        inventory: Inventory,
        registry: ItemRegistry,
        *,
        grid_size: int,
    ) -> bool:
        recipe = self.by_key(key)
        if not _fits_grid(recipe, grid_size, grid_size):
            return False
        candidate = inventory.clone()
        for item_id, count in recipe.required_items.items():
            if not candidate.remove(item_id, count):
                return False
        if candidate.add(recipe.result, registry) is not None:
            return False
        inventory.replace_from(candidate)
        return True


def _parse_recipe(raw: dict[str, object], registry: ItemRegistry) -> Recipe:
    key = _required_string(raw, "key")
    kind = _required_string(raw, "kind")
    result_id = registry.by_key(_required_string(raw, "result")).id
    result_count = raw.get("count", 1)
    if not isinstance(result_count, int) or result_count < 1:
        raise ValueError(f"Recipe {key} has an invalid result count")
    if kind == "shapeless":
        raw_ingredients = raw.get("ingredients")
        if not _is_string_list(raw_ingredients) or not raw_ingredients:
            raise ValueError(f"Shapeless recipe {key} needs ingredients")
        ingredients = tuple(registry.by_key(value).id for value in raw_ingredients)
        pattern = (ingredients,)
        shaped = False
    elif kind == "shaped":
        raw_pattern = raw.get("pattern")
        raw_keys = raw.get("keys")
        if not _is_string_list(raw_pattern) or not raw_pattern or not _is_string_dict(raw_keys):
            raise ValueError(f"Shaped recipe {key} needs pattern and keys")
        pattern_rows = raw_pattern
        key_map = raw_keys
        width = len(pattern_rows[0])
        if width < 1 or any(len(row) != width for row in pattern_rows):
            raise ValueError(f"Shaped recipe {key} rows must have equal width")
        resolved = {symbol: registry.by_key(item_key).id for symbol, item_key in key_map.items()}
        pattern = tuple(
            tuple(None if symbol == " " else resolved[symbol] for symbol in row)
            for row in pattern_rows
        )
        pattern = _trim_pattern(pattern)
        shaped = True
    else:
        raise ValueError(f"Unsupported recipe kind: {kind}")
    return Recipe(key, pattern, ItemStack(result_id, result_count), shaped)


def _required_string(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Recipe field {key} must be non-empty text")
    return value


def _is_string_list(value: object) -> TypeIs[list[str]]:
    if not isinstance(value, list):
        return False
    return all(isinstance(item, str) for item in cast(list[object], value))


def _is_string_dict(value: object) -> TypeIs[dict[str, str]]:
    if not isinstance(value, dict):
        return False
    items = cast(dict[object, object], value)
    return all(isinstance(key, str) and isinstance(item, str) for key, item in items.items())


def _trim_pattern(
    pattern: tuple[tuple[int | None, ...], ...],
) -> tuple[tuple[int | None, ...], ...]:
    if not pattern:
        return ()
    occupied_rows = [index for index, row in enumerate(pattern) if any(v is not None for v in row)]
    if not occupied_rows:
        return ()
    occupied_columns = [
        column
        for column in range(len(pattern[0]))
        if any(row[column] is not None for row in pattern)
    ]
    first_row, last_row = occupied_rows[0], occupied_rows[-1]
    first_column, last_column = occupied_columns[0], occupied_columns[-1]
    return tuple(
        tuple(row[first_column : last_column + 1]) for row in pattern[first_row : last_row + 1]
    )


def _fits_grid(recipe: Recipe, width: int, height: int) -> bool:
    if recipe.shaped:
        return recipe.width <= width and recipe.height <= height
    return sum(recipe.required_items.values()) <= width * height
