from __future__ import annotations

from voxel_sandbox.application.player_camera import (
    PerspectiveMode,
    camera_position_for_perspective,
    cycle_perspective_mode,
)


def test_cycle_perspective_mode_uses_minecraft_like_order() -> None:
    assert cycle_perspective_mode(PerspectiveMode.FIRST_PERSON) is PerspectiveMode.THIRD_PERSON_BACK
    assert (
        cycle_perspective_mode(PerspectiveMode.THIRD_PERSON_BACK)
        is PerspectiveMode.THIRD_PERSON_FRONT
    )
    assert (
        cycle_perspective_mode(PerspectiveMode.THIRD_PERSON_FRONT) is PerspectiveMode.FIRST_PERSON
    )


def test_first_person_camera_position_is_eye_position() -> None:
    eye = (1.0, 2.0, 3.0)

    assert (
        camera_position_for_perspective(
            eye,
            (1.0, 0.0, 0.0),
            PerspectiveMode.FIRST_PERSON,
        )
        == eye
    )


def test_third_person_back_offsets_behind_horizontal_view_direction() -> None:
    assert camera_position_for_perspective(
        (10.0, 5.0, 10.0),
        (1.0, -0.7, 0.0),
        PerspectiveMode.THIRD_PERSON_BACK,
        distance=4.0,
        height_offset=0.5,
    ) == (6.0, 5.5, 10.0)


def test_third_person_front_offsets_in_front_of_horizontal_view_direction() -> None:
    assert camera_position_for_perspective(
        (10.0, 5.0, 10.0),
        (0.0, 0.2, -2.0),
        PerspectiveMode.THIRD_PERSON_FRONT,
        distance=3.0,
        height_offset=0.25,
    ) == (10.0, 5.25, 7.0)
