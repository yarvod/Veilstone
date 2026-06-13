from __future__ import annotations

import math

from voxel_sandbox.render.camera import FirstPersonCamera, MovementIntent


def test_camera_moves_forward_using_yaw() -> None:
    camera = FirstPersonCamera(x=0.0, y=0.0, z=0.0, yaw_degrees=-90.0)

    camera.move(MovementIntent(forward=1.0), speed=4.0, delta_time=0.5)

    assert math.isclose(camera.x, 0.0, abs_tol=1e-7)
    assert math.isclose(camera.z, -2.0)


def test_diagonal_camera_movement_is_normalized() -> None:
    camera = FirstPersonCamera(x=0.0, y=0.0, z=0.0, yaw_degrees=0.0)

    camera.move(MovementIntent(forward=1.0, right=1.0), speed=10.0, delta_time=1.0)

    assert math.isclose(camera.x**2 + camera.z**2, 100.0)


def test_camera_pitch_is_clamped() -> None:
    camera = FirstPersonCamera(pitch_degrees=0.0)

    camera.rotate(delta_x=0.0, delta_y=2000.0, sensitivity=1.0)
    assert camera.pitch_degrees == 89.0

    camera.rotate(delta_x=0.0, delta_y=-4000.0, sensitivity=1.0)
    assert camera.pitch_degrees == -89.0
