from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

BlockGetter = Callable[[int, int, int], int]


@dataclass(frozen=True, slots=True)
class PlayerInput:
    forward: float = 0.0
    right: float = 0.0
    jump: bool = False


@dataclass(slots=True)
class PlayerController:
    x: float = 8.0
    y: float = 58.0
    z: float = 8.0
    velocity_y: float = 0.0
    on_ground: bool = False
    width: float = 0.6
    height: float = 1.8
    eye_height: float = 1.62
    walk_speed: float = 5.0
    jump_speed: float = 8.0
    gravity: float = 24.0

    @property
    def eye_position(self) -> tuple[float, float, float]:
        return self.x, self.y + self.eye_height, self.z

    def update(
        self,
        player_input: PlayerInput,
        yaw_degrees: float,
        delta_time: float,
        get_block: BlockGetter,
    ) -> None:
        if player_input.jump and self.on_ground:
            self.velocity_y = self.jump_speed
            self.on_ground = False
        self.velocity_y -= self.gravity * delta_time

        length = math.hypot(player_input.forward, player_input.right)
        forward = player_input.forward / max(1.0, length)
        right = player_input.right / max(1.0, length)
        yaw = math.radians(yaw_degrees)
        forward_x, forward_z = math.cos(yaw), math.sin(yaw)
        right_x, right_z = -forward_z, forward_x
        delta_x = (forward_x * forward + right_x * right) * self.walk_speed * delta_time
        delta_z = (forward_z * forward + right_z * right) * self.walk_speed * delta_time

        self._move_axis("x", delta_x, get_block)
        self._move_axis("z", delta_z, get_block)
        collided_y = self._move_axis("y", self.velocity_y * delta_time, get_block)
        if collided_y:
            self.on_ground = self.velocity_y < 0.0
            self.velocity_y = 0.0
        elif self.velocity_y > 0.0:
            self.on_ground = False

    def intersects_block(self, block: tuple[int, int, int]) -> bool:
        bx, by, bz = block
        half = self.width / 2.0
        return (
            self.x + half > bx
            and self.x - half < bx + 1
            and self.y + self.height > by
            and self.y < by + 1
            and self.z + half > bz
            and self.z - half < bz + 1
        )

    def _move_axis(self, axis: str, displacement: float, get_block: BlockGetter) -> bool:
        if displacement == 0.0:
            return False
        steps = max(1, math.ceil(abs(displacement) / 0.2))
        step = displacement / steps
        for _ in range(steps):
            previous = getattr(self, axis)
            setattr(self, axis, previous + step)
            if self._collides(get_block):
                setattr(self, axis, previous)
                return True
        return False

    def _collides(self, get_block: BlockGetter) -> bool:
        epsilon = 1e-7
        half = self.width / 2.0
        min_x = math.floor(self.x - half + epsilon)
        max_x = math.floor(self.x + half - epsilon)
        min_y = math.floor(self.y + epsilon)
        max_y = math.floor(self.y + self.height - epsilon)
        min_z = math.floor(self.z - half + epsilon)
        max_z = math.floor(self.z + half - epsilon)
        return any(
            get_block(x, y, z) != 0
            for x in range(min_x, max_x + 1)
            for y in range(min_y, max_y + 1)
            for z in range(min_z, max_z + 1)
        )
