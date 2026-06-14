from __future__ import annotations

import math
import random
from collections.abc import Callable

from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemRegistry, ItemStack
from voxel_sandbox.engine.ecs.components import (
    AnimationState,
    Collider,
    EntityId,
    Health,
    ItemEntity,
    Lifetime,
    MobAI,
    MobKind,
    MobState,
    RenderModel,
    Transform,
    Velocity,
)
from voxel_sandbox.engine.ecs.world import EntityWorld


class EntitySimulation:
    def __init__(self, seed: int = 0) -> None:
        self.world = EntityWorld()
        self._random = random.Random(seed)

    def spawn_item(
        self,
        position: tuple[float, float, float],
        stack: ItemStack,
    ) -> EntityId:
        entity = self.world.create()
        self.world.transforms.set(entity, Transform(*position))
        self.world.items.set(entity, ItemEntity(stack))
        self.world.lifetimes.set(entity, Lifetime(300.0))
        self.world.render_models.set(
            entity,
            RenderModel("item", (0.95, 0.75, 0.25), (0.28, 0.28, 0.28)),
        )
        return entity

    def spawn_mob(
        self,
        kind: MobKind,
        position: tuple[float, float, float],
    ) -> EntityId:
        entity = self.world.create()
        self.world.transforms.set(entity, Transform(*position))
        self.world.velocities.set(entity, Velocity())
        self.world.colliders.set(entity, Collider(0.7, 1.2))
        self.world.health.set(entity, Health(10.0 if kind is MobKind.PASSIVE else 16.0, 16.0))
        self.world.mob_ai.set(entity, MobAI(kind))
        self.world.animations.set(entity, AnimationState())
        color = (0.34, 0.58, 0.68) if kind is MobKind.PASSIVE else (0.62, 0.18, 0.28)
        self.world.render_models.set(entity, RenderModel(kind.value, color, (0.7, 1.2, 0.7)))
        return entity

    def maintain_population(
        self,
        center: tuple[float, float, float],
        ground_height: Callable[[int, int], int],
        is_hazard: Callable[[int, int, int], bool],
        *,
        passive_count: int = 3,
        hostile_count: int = 1,
        hostile_spawn_allowed: Callable[[int, int, int], bool] | None = None,
    ) -> None:
        counts = {MobKind.PASSIVE: 0, MobKind.HOSTILE: 0}
        for entity, ai in tuple(self.world.mob_ai.items()):
            if ai.kind is MobKind.HOSTILE and hostile_count <= 0:
                self.world.destroy(entity)
                continue
            counts[ai.kind] += 1
        for kind, desired in (
            (MobKind.PASSIVE, passive_count),
            (MobKind.HOSTILE, hostile_count),
        ):
            missing = desired - counts[kind]
            attempts = 0
            while missing > 0 and attempts < desired * 12:
                attempts += 1
                angle = self._random.random() * math.tau
                radius = 6.0 + self._random.random() * 6.0
                x = center[0] + math.cos(angle) * radius
                z = center[2] + math.sin(angle) * radius
                block_x = math.floor(x)
                block_z = math.floor(z)
                ground = ground_height(block_x, block_z)
                if is_hazard(block_x, ground, block_z):
                    continue
                if (
                    kind is MobKind.HOSTILE
                    and hostile_spawn_allowed is not None
                    and not hostile_spawn_allowed(block_x, ground, block_z)
                ):
                    continue
                self.spawn_mob(kind, (x, float(ground), z))
                missing -= 1

    def update(
        self,
        delta_time: float,
        player_position: tuple[float, float, float],
        ground_height: Callable[[int, int], int],
        is_hazard: Callable[[int, int, int], bool],
    ) -> float:
        player_damage = 0.0
        for entity, lifetime in tuple(self.world.lifetimes.items()):
            lifetime.remaining -= delta_time
            if lifetime.remaining <= 0.0:
                self.world.destroy(entity)

        for entity, ai in tuple(self.world.mob_ai.items()):
            transform = self.world.transforms[entity]
            animation = self.world.animations[entity]
            animation.phase += delta_time * max(animation.speed, 0.35)
            if animation.death_remaining > 0.0:
                animation.death_remaining -= delta_time
                ai.state = MobState.DEATH
                _advance_animation_state(animation, ai.state, delta_time)
                if animation.death_remaining <= 0.0:
                    self.world.destroy(entity)
                continue
            if animation.hurt_remaining > 0.0:
                animation.hurt_remaining -= delta_time
                ai.state = MobState.HURT
                _advance_animation_state(animation, ai.state, delta_time)
                continue
            dx = player_position[0] - transform.x
            dz = player_position[2] - transform.z
            distance = math.hypot(dx, dz)
            if distance > 48.0:
                self.world.destroy(entity)
                continue
            ai.attack_cooldown = max(0.0, ai.attack_cooldown - delta_time)
            ai.state_time -= delta_time
            speed = 0.0
            if ai.kind is MobKind.HOSTILE and distance <= 1.5:
                ai.state = MobState.ATTACK
                if ai.attack_cooldown == 0.0:
                    player_damage += 2.0
                    ai.attack_cooldown = 1.0
            elif ai.kind is MobKind.HOSTILE and distance <= 14.0:
                ai.state = MobState.CHASE
                ai.direction_x, ai.direction_z = _normalized(dx, dz)
                speed = 2.2
            else:
                if ai.state_time <= 0.0 or ai.state in {MobState.CHASE, MobState.ATTACK}:
                    ai.state = MobState.WANDER
                    angle = self._random.random() * math.tau
                    ai.direction_x, ai.direction_z = math.cos(angle), math.sin(angle)
                    ai.state_time = 1.5 + self._random.random() * 3.0
                speed = 1.1 if ai.kind is MobKind.PASSIVE else 1.4
            next_x = transform.x + ai.direction_x * speed * delta_time
            next_z = transform.z + ai.direction_z * speed * delta_time
            ground = ground_height(math.floor(next_x), math.floor(next_z))
            if is_hazard(math.floor(next_x), ground, math.floor(next_z)):
                ai.direction_x *= -1.0
                ai.direction_z *= -1.0
                ai.state_time = 0.5
                continue
            transform.x = next_x
            transform.z = next_z
            transform.y = float(ground)
            velocity = self.world.velocities[entity]
            velocity.x = ai.direction_x * speed
            velocity.z = ai.direction_z * speed
            animation.speed = speed
            _advance_animation_state(animation, ai.state, delta_time)
            if speed > 0.0:
                transform.yaw = math.atan2(ai.direction_x, ai.direction_z)
        return player_damage

    def damage(self, entity: EntityId, amount: float) -> tuple[ItemStack, ...]:
        health = self.world.health.get(entity)
        ai = self.world.mob_ai.get(entity)
        transform = self.world.transforms.get(entity)
        animation = self.world.animations.get(entity)
        if health is None or ai is None or transform is None or animation is None:
            return ()
        if health.current <= 0.0:
            return ()
        if not health.damage(amount):
            animation.hurt_remaining = 0.25
            ai.state = MobState.HURT
            return ()
        drops = (ItemStack(4, 1),) if ai.kind is MobKind.PASSIVE else (ItemStack(6, 1),)
        position = transform.position
        ai.state = MobState.DEATH
        animation.death_remaining = 0.65
        animation.speed = 0.0
        velocity = self.world.velocities.get(entity)
        if velocity is not None:
            velocity.x = 0.0
            velocity.z = 0.0
        for stack in drops:
            self.spawn_item(position, stack)
        return drops

    def pickup_items(
        self,
        position: tuple[float, float, float],
        radius: float,
        inventory: Inventory,
        registry: ItemRegistry,
    ) -> tuple[ItemStack, ...]:
        picked: list[ItemStack] = []
        radius_squared = radius * radius
        for entity, item in tuple(self.world.items.items()):
            transform = self.world.transforms[entity]
            distance_squared = sum(
                (transform.position[index] - position[index]) ** 2 for index in range(3)
            )
            if distance_squared > radius_squared:
                continue
            remainder = inventory.add(item.stack, registry)
            accepted = item.stack.count - (remainder.count if remainder else 0)
            if accepted:
                picked.append(item.stack.with_count(accepted))
            if remainder is None:
                self.world.destroy(entity)
            else:
                self.world.items.set(entity, ItemEntity(remainder))
        return tuple(picked)

    def target_mob(
        self,
        origin: tuple[float, float, float],
        direction: tuple[float, float, float],
        max_distance: float = 5.0,
    ) -> EntityId | None:
        best: tuple[float, EntityId] | None = None
        for entity, ai in self.world.mob_ai.items():
            health = self.world.health.get(entity)
            if ai.state is MobState.DEATH or health is None or health.current <= 0.0:
                continue
            transform = self.world.transforms[entity]
            offset = (
                transform.x - origin[0],
                transform.y + 0.6 - origin[1],
                transform.z - origin[2],
            )
            projected = sum(offset[index] * direction[index] for index in range(3))
            if not 0.0 <= projected <= max_distance:
                continue
            perpendicular_squared = sum(value * value for value in offset) - projected**2
            if perpendicular_squared <= 0.6**2 and (best is None or projected < best[0]):
                best = projected, entity
        return best[1] if best else None


def _normalized(x: float, z: float) -> tuple[float, float]:
    length = math.hypot(x, z)
    if length <= 1e-9:
        return 0.0, 0.0
    return x / length, z / length


def _advance_animation_state(
    animation: AnimationState,
    state: MobState,
    delta_time: float,
) -> None:
    if animation.state is not state:
        animation.state = state
        animation.state_phase = 0.0
    else:
        animation.state_phase += delta_time
