from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.render.camera import FirstPersonCamera


def camera_matrix(
    camera: FirstPersonCamera,
    aspect_ratio: float,
    field_of_view: float,
) -> NDArray[np.float32]:
    projection = _perspective(field_of_view, aspect_ratio, 0.1, 256.0)
    yaw = math.radians(camera.yaw_degrees)
    pitch = math.radians(camera.pitch_degrees)
    forward = np.asarray(
        (math.cos(yaw) * math.cos(pitch), math.sin(pitch), math.sin(yaw) * math.cos(pitch)),
        dtype=np.float32,
    )
    eye = np.asarray(camera.position, dtype=np.float32)
    view = _look_at(eye, eye + forward, np.asarray((0.0, 1.0, 0.0), dtype=np.float32))
    return projection @ view


def _perspective(fov_degrees: float, aspect: float, near: float, far: float) -> NDArray[np.float32]:
    scale = 1.0 / math.tan(math.radians(fov_degrees) / 2.0)
    result = np.zeros((4, 4), dtype=np.float32)
    result[0, 0] = scale / aspect
    result[1, 1] = scale
    result[2, 2] = (far + near) / (near - far)
    result[2, 3] = (2.0 * far * near) / (near - far)
    result[3, 2] = -1.0
    return result


def _look_at(
    eye: NDArray[np.float32],
    target: NDArray[np.float32],
    up: NDArray[np.float32],
) -> NDArray[np.float32]:
    forward = target - eye
    forward /= np.linalg.norm(forward)
    side = np.cross(forward, up)
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
