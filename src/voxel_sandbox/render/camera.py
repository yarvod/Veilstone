from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MovementIntent:
    forward: float = 0.0
    right: float = 0.0
    up: float = 0.0


@dataclass(slots=True)
class FirstPersonCamera:
    x: float = 8.0
    y: float = 58.0
    z: float = 8.0
    yaw_degrees: float = -90.0
    pitch_degrees: float = -35.0

    @property
    def position(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    @position.setter
    def position(self, value: tuple[float, float, float]) -> None:
        self.x, self.y, self.z = value

    @property
    def direction(self) -> tuple[float, float, float]:
        yaw = math.radians(self.yaw_degrees)
        pitch = math.radians(self.pitch_degrees)
        return (
            math.cos(yaw) * math.cos(pitch),
            math.sin(pitch),
            math.sin(yaw) * math.cos(pitch),
        )

    def rotate(self, delta_x: float, delta_y: float, sensitivity: float) -> None:
        self.yaw_degrees += delta_x * sensitivity
        self.pitch_degrees = max(
            -89.0,
            min(89.0, self.pitch_degrees + delta_y * sensitivity),
        )

    def move(self, intent: MovementIntent, speed: float, delta_time: float) -> None:
        length = math.sqrt(intent.forward**2 + intent.right**2 + intent.up**2)
        if length == 0.0:
            return

        scale = speed * delta_time / max(1.0, length)
        yaw = math.radians(self.yaw_degrees)
        forward_x = math.cos(yaw)
        forward_z = math.sin(yaw)
        right_x = -forward_z
        right_z = forward_x

        self.x += (forward_x * intent.forward + right_x * intent.right) * scale
        self.y += intent.up * scale
        self.z += (forward_z * intent.forward + right_z * intent.right) * scale
