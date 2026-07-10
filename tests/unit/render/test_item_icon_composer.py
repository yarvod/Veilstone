from __future__ import annotations

from typing import cast

from PIL import Image

from voxel_sandbox.render.model_snapshots import BlockModelSnapshot, ItemModelSnapshot
from voxel_sandbox.render.ui.item_icon_composer import (
    compose_isometric_block_icon,
    compose_item_model_icon,
)

type RgbaPixel = tuple[int, int, int, int]


def _pixel(image: Image.Image, position: tuple[int, int]) -> RgbaPixel:
    return cast(RgbaPixel, image.getpixel(position))


def _block_item_model() -> ItemModelSnapshot:
    return ItemModelSnapshot(
        item_id=3,
        key="test_block",
        name="Test Block",
        item_type="block",
        block=BlockModelSnapshot(
            block_id=3,
            key="test_block",
            name="Test Block",
            texture_top="test:top",
            texture_side="test:side",
            texture_bottom="test:bottom",
            tint_top=None,
            tint_side=None,
            tint_bottom=None,
            render_layer="opaque",
            render_shape="cube",
            wind_motion="none",
        ),
    )


def test_item_model_icon_uses_distinct_top_and_side_texture_slots() -> None:
    atlas = Image.new("RGBA", (8, 4))
    atlas.paste((240, 40, 30, 255), (0, 0, 4, 4))
    atlas.paste((20, 220, 70, 255), (4, 0, 8, 4))
    icon = compose_item_model_icon(
        _block_item_model(),
        atlas,
        {
            "test:top": (0.0, 0.0, 0.5, 1.0),
            "test:side": (0.5, 0.0, 1.0, 1.0),
        },
    )

    assert icon is not None
    assert icon.size == (32, 32)
    assert _pixel(icon, (16, 6)) == (240, 40, 30, 255)
    left = _pixel(icon, (8, 17))
    right = _pixel(icon, (24, 17))
    assert left[1] > left[0]
    assert right[1] > right[0]
    assert left[1] > right[1]


def test_isometric_icon_preserves_transparent_background_and_cutouts() -> None:
    top = Image.new("RGBA", (4, 4), (210, 170, 80, 255))
    top.putpixel((2, 2), (0, 0, 0, 0))
    side = Image.new("RGBA", (4, 4), (80, 140, 210, 255))

    icon = compose_isometric_block_icon(top, side)

    assert _pixel(icon, (0, 0))[3] == 0
    assert _pixel(icon, (31, 31))[3] == 0
    assert _pixel(icon, (16, 8))[3] == 0
    assert icon.getbbox() is not None


def test_isometric_top_face_keeps_nearest_neighbor_pixel_colors() -> None:
    top = Image.new("RGBA", (2, 2))
    top.putpixel((0, 0), (255, 0, 0, 255))
    top.putpixel((1, 0), (0, 0, 255, 255))
    top.putpixel((0, 1), (0, 0, 255, 255))
    top.putpixel((1, 1), (255, 0, 0, 255))
    side = Image.new("RGBA", (2, 2), (0, 255, 0, 255))

    icon = compose_isometric_block_icon(top, side)
    top_colors = {
        _pixel(icon, (x, y))
        for y in range(2, 8)
        for x in range(4, 29)
        if _pixel(icon, (x, y))[3] > 0
    }

    assert top_colors == {(255, 0, 0, 255), (0, 0, 255, 255)}


def test_non_block_model_defers_to_existing_fallback_icon_path() -> None:
    model = ItemModelSnapshot(
        item_id=6,
        key="resource",
        name="Resource",
        item_type="resource",
    )

    assert compose_item_model_icon(model, Image.new("RGBA", (1, 1)), {}) is None
