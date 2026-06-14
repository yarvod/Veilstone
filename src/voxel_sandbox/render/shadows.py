from __future__ import annotations

import math
from dataclasses import dataclass

import moderngl
import numpy as np
from numpy.typing import NDArray


def shadow_map_size(quality: str) -> int:
    return {"off": 0, "low": 1024, "medium": 2048}.get(quality, 2048)


def sun_light_matrix(
    center: tuple[float, float, float],
    *,
    map_size: int,
    radius: float = 48.0,
) -> NDArray[np.float32]:
    direction = np.asarray((0.4, 0.8, 0.25), dtype=np.float32)
    direction /= np.linalg.norm(direction)
    target = np.asarray(center, dtype=np.float32)
    texel_world_size = (radius * 2.0) / max(map_size, 1)
    target[0] = round(float(target[0]) / texel_world_size) * texel_world_size
    target[2] = round(float(target[2]) / texel_world_size) * texel_world_size
    eye = (target + direction * radius).astype(np.float32)
    return _orthographic(-radius, radius, -radius, radius, 0.1, radius * 3.0) @ _look_at(
        eye,
        target,
        np.asarray((0.0, 1.0, 0.0), dtype=np.float32),
    )


@dataclass(slots=True)
class ShadowMap:
    size: int
    texture: moderngl.Texture
    framebuffer: moderngl.Framebuffer

    @classmethod
    def create(cls, context: moderngl.Context, size: int) -> ShadowMap:
        texture = context.depth_texture((size, size))
        texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        texture.repeat_x = False
        texture.repeat_y = False
        texture.compare_func = "<="
        return cls(size, texture, context.framebuffer(depth_attachment=texture))

    def release(self) -> None:
        self.framebuffer.release()
        self.texture.release()


def _orthographic(
    left: float,
    right: float,
    bottom: float,
    top: float,
    near: float,
    far: float,
) -> NDArray[np.float32]:
    result = np.identity(4, dtype=np.float32)
    result[0, 0] = 2.0 / (right - left)
    result[1, 1] = 2.0 / (top - bottom)
    result[2, 2] = -2.0 / (far - near)
    result[0, 3] = -(right + left) / (right - left)
    result[1, 3] = -(top + bottom) / (top - bottom)
    result[2, 3] = -(far + near) / (far - near)
    return result


def _look_at(
    eye: NDArray[np.float32],
    target: NDArray[np.float32],
    up: NDArray[np.float32],
) -> NDArray[np.float32]:
    forward = target - eye
    forward /= np.linalg.norm(forward)
    side = np.cross(forward, up)
    if math.isclose(float(np.linalg.norm(side)), 0.0):
        raise ValueError("Sun direction cannot be parallel to the up vector")
    side /= np.linalg.norm(side)
    camera_up = np.cross(side, forward)
    result = np.identity(4, dtype=np.float32)
    result[0, :3] = side
    result[1, :3] = camera_up
    result[2, :3] = -forward
    result[0, 3] = -np.dot(side, eye)
    result[1, 3] = -np.dot(camera_up, eye)
    result[2, 3] = np.dot(forward, eye)
    return result
