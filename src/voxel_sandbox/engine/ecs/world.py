from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from voxel_sandbox.engine.ecs.components import (
    Collider,
    EntityId,
    Health,
    ItemEntity,
    Lifetime,
    MobAI,
    RenderModel,
    Transform,
    Velocity,
)


class ComponentStore[T]:
    def __init__(self) -> None:
        self._components: dict[EntityId, T] = {}

    def __contains__(self, entity: EntityId) -> bool:
        return entity in self._components

    def __getitem__(self, entity: EntityId) -> T:
        return self._components[entity]

    def get(self, entity: EntityId) -> T | None:
        return self._components.get(entity)

    def set(self, entity: EntityId, component: T) -> None:
        self._components[entity] = component

    def remove(self, entity: EntityId) -> None:
        self._components.pop(entity, None)

    def items(self) -> Iterator[tuple[EntityId, T]]:
        return iter(self._components.items())

    def entities(self) -> set[EntityId]:
        return set(self._components)

    def __len__(self) -> int:
        return len(self._components)


class EntityCollection(Protocol):
    def entities(self) -> set[EntityId]: ...


class EntityWorld:
    def __init__(self) -> None:
        self._next_id: EntityId = 1
        self.alive: set[EntityId] = set()
        self.transforms: ComponentStore[Transform] = ComponentStore()
        self.velocities: ComponentStore[Velocity] = ComponentStore()
        self.colliders: ComponentStore[Collider] = ComponentStore()
        self.health: ComponentStore[Health] = ComponentStore()
        self.render_models: ComponentStore[RenderModel] = ComponentStore()
        self.mob_ai: ComponentStore[MobAI] = ComponentStore()
        self.lifetimes: ComponentStore[Lifetime] = ComponentStore()
        self.items: ComponentStore[ItemEntity] = ComponentStore()
        self._stores = (
            self.transforms,
            self.velocities,
            self.colliders,
            self.health,
            self.render_models,
            self.mob_ai,
            self.lifetimes,
            self.items,
        )

    def create(self) -> EntityId:
        entity = self._next_id
        self._next_id += 1
        self.alive.add(entity)
        return entity

    def destroy(self, entity: EntityId) -> None:
        self.alive.discard(entity)
        for store in self._stores:
            store.remove(entity)

    def query(self, *stores: EntityCollection) -> tuple[EntityId, ...]:
        if not stores:
            return tuple(self.alive)
        entities = stores[0].entities()
        for store in stores[1:]:
            entities.intersection_update(store.entities())
        return tuple(sorted(entities))
