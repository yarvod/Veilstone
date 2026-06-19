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
        collider = Collider(0.9, 1.4) if kind is MobKind.PASSIVE else Collider(0.65, 1.85)
        self.world.colliders.set(entity, collider)
        maximum_health = 10.0 if kind is MobKind.PASSIVE else 16.0
        self.world.health.set(entity, Health(maximum_health, maximum_health))
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
        is_solid: Callable[[int, int, int], bool] | None = None,
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
                if is_solid is not None and (
                    is_solid(block_x, ground, block_z) or is_solid(block_x, ground + 1, block_z)
                ):
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
        is_solid: Callable[[int, int, int], bool] | None = None,
    ) -> float:
        player_damage = 0.0
        for entity, lifetime in tuple(self.world.lifetimes.items()):
            lifetime.remaining -= delta_time
            if lifetime.remaining <= 0.0:
                self.world.destroy(entity)

        for entity, ai in tuple(self.world.mob_ai.items()):
            transform = self.world.transforms[entity]
            animation = self.world.animations[entity]
            collider = self.world.colliders[entity]
            velocity = self.world.velocities[entity]
            if is_solid is not None:
                _update_vertical(transform, velocity, collider, delta_time, is_solid, is_hazard)
            animation.phase += delta_time
            if ai.knockback_remaining > 0.0:
                ai.knockback_remaining = max(0.0, ai.knockback_remaining - delta_time)
                _move_knockback(
                    transform,
                    velocity,
                    collider,
                    delta_time,
                    is_hazard,
                    is_solid,
                )
                damping = max(0.0, 1.0 - 6.5 * delta_time)
                velocity.x *= damping
                velocity.z *= damping
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
            if ai.state is MobState.HURT:
                ai.state = MobState.FLEE if ai.kind is MobKind.PASSIVE else MobState.CHASE
            dx = player_position[0] - transform.x
            dz = player_position[2] - transform.z
            distance = math.hypot(dx, dz)
            if distance > 48.0:
                self.world.destroy(entity)
                continue
            ai.attack_cooldown = max(0.0, ai.attack_cooldown - delta_time)
            ai.state_time -= delta_time
            speed = 0.0
            dy = player_position[1] - transform.y
            if ai.kind is MobKind.HOSTILE and distance <= 1.5 and abs(dy) <= 2.0:
                ai.state = MobState.ATTACK
                if ai.attack_cooldown == 0.0:
                    player_damage += 2.0
                    ai.attack_cooldown = 1.0
                    animation.state_phase = 0.0
            elif ai.kind is MobKind.HOSTILE and distance <= 14.0:
                ai.state = MobState.CHASE
                ai.direction_x, ai.direction_z = _normalized(dx, dz)
                speed = 2.2
            else:
                if ai.state_time <= 0.0 or ai.state in {MobState.CHASE, MobState.ATTACK}:
                    choice = self._random.random()
                    if choice < 0.34:
                        ai.state = MobState.IDLE
                        ai.direction_x = ai.direction_z = 0.0
                        ai.state_time = 2.0 + self._random.random() * 3.0
                    elif choice < 0.68 and ai.kind is MobKind.PASSIVE:
                        ai.state = MobState.GRAZE
                        ai.direction_x = ai.direction_z = 0.0
                        ai.state_time = 3.5 + self._random.random() * 3.5
                    else:
                        ai.state = MobState.WANDER
                        angle = self._random.random() * math.tau
                        ai.direction_x, ai.direction_z = math.cos(angle), math.sin(angle)
                        ai.state_time = 2.5 + self._random.random() * 4.0
                if ai.state in {MobState.IDLE, MobState.GRAZE}:
                    speed = 0.0
                elif ai.state is MobState.FLEE:
                    speed = 2.35
                else:
                    speed = 0.72 if ai.kind is MobKind.PASSIVE else 1.05
            actual_speed = 0.0
            move_x = 0.0
            move_z = 0.0
            if speed > 0.0:
                target_yaw = math.atan2(ai.direction_x, -ai.direction_z)
                transform.yaw = _approach_angle(transform.yaw, target_yaw, delta_time * 3.8)
                facing_x = math.sin(transform.yaw)
                facing_z = -math.cos(transform.yaw)
                alignment = max(0.0, facing_x * ai.direction_x + facing_z * ai.direction_z)
                actual_speed = speed * (0.2 + 0.8 * alignment)
                move_x = facing_x * actual_speed
                move_z = facing_z * actual_speed
            next_x = transform.x + move_x * delta_time
            next_z = transform.z + move_z * delta_time
            ground = ground_height(math.floor(next_x), math.floor(next_z))
            hazard_y = math.floor(transform.y) if is_solid is not None else ground
            if is_hazard(math.floor(next_x), hazard_y, math.floor(next_z)):
                ai.direction_x *= -1.0
                ai.direction_z *= -1.0
                ai.state_time = 0.5
            else:
                if is_solid is not None and _mob_collides(
                    next_x, transform.y, next_z, collider, is_solid
                ):
                    if not _mob_collides(next_x, transform.y + 1.0, next_z, collider, is_solid):
                        transform.y += 1.0
                        transform.x = next_x
                        transform.z = next_z
                    else:
                        avoided = False
                        for turn_angle in (0.7, -0.7, 1.4, -1.4):
                            cos_a = math.cos(turn_angle)
                            sin_a = math.sin(turn_angle)
                            new_dx = ai.direction_x * cos_a - ai.direction_z * sin_a
                            new_dz = ai.direction_x * sin_a + ai.direction_z * cos_a
                            alt_x = transform.x + new_dx * speed * delta_time
                            alt_z = transform.z + new_dz * speed * delta_time
                            if not _mob_collides(alt_x, transform.y, alt_z, collider, is_solid):
                                ai.direction_x, ai.direction_z = new_dx, new_dz
                                transform.x = alt_x
                                transform.z = alt_z
                                avoided = True
                                break
                        if not avoided:
                            ai.direction_x *= -1.0
                            ai.direction_z *= -1.0
                            ai.state_time = 0.5
                else:
                    transform.x = next_x
                    transform.z = next_z
            velocity.x = move_x
            velocity.z = move_z
            if is_solid is None:
                transform.y = float(ground)
            animation.speed = actual_speed
            _advance_animation_state(animation, ai.state, delta_time)
        return player_damage

    def damage(
        self,
        entity: EntityId,
        amount: float,
        source_position: tuple[float, float, float] | None = None,
    ) -> tuple[ItemStack, ...]:
        health = self.world.health.get(entity)
        ai = self.world.mob_ai.get(entity)
        transform = self.world.transforms.get(entity)
        animation = self.world.animations.get(entity)
        if health is None or ai is None or transform is None or animation is None:
            return ()
        if health.current <= 0.0:
            return ()
        velocity = self.world.velocities.get(entity)
        if velocity is not None:
            away_x, away_z = _damage_direction(transform, source_position)
            velocity.x = away_x * 5.2
            velocity.z = away_z * 5.2
            velocity.y = max(velocity.y, 3.8)
            ai.knockback_remaining = 0.32
            ai.direction_x = away_x
            ai.direction_z = away_z
            ai.state_time = 2.8 if ai.kind is MobKind.PASSIVE else 0.8
        if not health.damage(amount):
            animation.hurt_remaining = 0.25
            ai.state = MobState.HURT
            return ()
        drops = (ItemStack(4, 1),) if ai.kind is MobKind.PASSIVE else (ItemStack(6, 1),)
        position = transform.position
        ai.state = MobState.DEATH
        animation.death_remaining = 0.65
        animation.speed = 0.0
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


def _approach_angle(current: float, target: float, maximum_delta: float) -> float:
    difference = (target - current + math.pi) % math.tau - math.pi
    difference = max(-maximum_delta, min(maximum_delta, difference))
    return current + difference


def _damage_direction(
    transform: Transform,
    source_position: tuple[float, float, float] | None,
) -> tuple[float, float]:
    if source_position is not None:
        direction = _normalized(transform.x - source_position[0], transform.z - source_position[2])
        if direction != (0.0, 0.0):
            return direction
    return -math.sin(transform.yaw), math.cos(transform.yaw)


def _move_knockback(
    transform: Transform,
    velocity: Velocity,
    collider: Collider,
    delta_time: float,
    is_hazard: Callable[[int, int, int], bool],
    is_solid: Callable[[int, int, int], bool] | None,
) -> None:
    next_x = transform.x + velocity.x * delta_time
    next_z = transform.z + velocity.z * delta_time
    if is_hazard(math.floor(next_x), math.floor(transform.y), math.floor(next_z)):
        velocity.x = velocity.z = 0.0
        return
    if is_solid is not None and _mob_collides(
        next_x,
        transform.y,
        next_z,
        collider,
        is_solid,
    ):
        velocity.x = velocity.z = 0.0
        return
    transform.x = next_x
    transform.z = next_z


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


def _mob_collides(
    x: float,
    y: float,
    z: float,
    collider: Collider,
    is_solid: Callable[[int, int, int], bool],
) -> bool:
    half = collider.width * 0.5
    epsilon = 1e-6
    return any(
        is_solid(block_x, block_y, block_z)
        for block_x in range(math.floor(x - half + epsilon), math.floor(x + half - epsilon) + 1)
        for block_y in range(math.floor(y + epsilon), math.floor(y + collider.height - epsilon) + 1)
        for block_z in range(math.floor(z - half + epsilon), math.floor(z + half - epsilon) + 1)
    )


def _update_vertical(
    transform: Transform,
    velocity: Velocity,
    collider: Collider,
    delta_time: float,
    is_solid: Callable[[int, int, int], bool],
    is_fluid: Callable[[int, int, int], bool],
) -> None:
    block_x = math.floor(transform.x)
    block_z = math.floor(transform.z)
    in_water = is_fluid(block_x, math.floor(transform.y + 0.35), block_z)
    if in_water:
        target_float_speed = 1.5
        velocity.y += (target_float_speed - velocity.y) * min(1.0, 5.0 * delta_time)
    else:
        velocity.y = max(-24.0, velocity.y - 20.0 * delta_time)
    displacement = velocity.y * delta_time
    steps = max(1, math.ceil(abs(displacement) / 0.18))
    step = displacement / steps
    for _ in range(steps):
        next_y = transform.y + step
        if _mob_collides(transform.x, next_y, transform.z, collider, is_solid):
            if step < 0.0:
                transform.y = float(math.floor(next_y) + 1)
            velocity.y = 0.0
            return
        transform.y = max(0.0, next_y)
