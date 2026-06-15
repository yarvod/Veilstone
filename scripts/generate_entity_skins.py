from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 256
TILE = 64
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "entities"


def _tile(draw: ImageDraw.ImageDraw, column: int, row: int, color: tuple[int, int, int]) -> None:
    x = column * TILE
    y = row * TILE
    draw.rectangle((x, y, x + TILE - 1, y + TILE - 1), fill=color)
    for offset in range(0, TILE, 8):
        shade = 5 if (offset // 8) % 2 == 0 else -4
        varied = tuple(max(0, min(255, channel + shade)) for channel in color)
        draw.rectangle((x + offset, y, x + offset + 7, y + 7), fill=varied)
        draw.rectangle((x, y + offset, x + 7, y + offset + 7), fill=varied)


def _rect(
    draw: ImageDraw.ImageDraw,
    column: int,
    row: int,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> None:
    x = column * TILE
    y = row * TILE
    draw.rectangle((x + box[0], y + box[1], x + box[2], y + box[3]), fill=color)


def _cow_skin() -> Image.Image:
    image = Image.new("RGB", (SIZE, SIZE), (84, 58, 42))
    draw = ImageDraw.Draw(image)
    brown = (91, 61, 43)
    dark = (55, 38, 29)
    cream = (220, 204, 173)
    pink = (190, 119, 112)
    black = (24, 21, 19)

    for column in range(4):
        _tile(draw, column, 0, brown)
        _tile(draw, column, 1, (105, 73, 51))
        _tile(draw, column, 2, (78, 52, 38))
    for column, row in ((0, 3), (1, 3)):
        _tile(draw, column, row, brown)
    _tile(draw, 2, 3, dark)
    _tile(draw, 3, 3, dark)

    # Body faces: broad irregular patches, never facial features.
    for column, patches in enumerate(
        (
            ((5, 8, 24, 27), (38, 33, 59, 54)),
            ((8, 34, 29, 58), (39, 5, 58, 22)),
            ((4, 5, 20, 19), (28, 37, 52, 59)),
            ((7, 27, 27, 52), (40, 8, 59, 27)),
        )
    ):
        for patch in patches:
            _rect(draw, column, 0, patch, cream)

    # Head front only: eyes and muzzle are deliberately absent from side/back tiles.
    _rect(draw, 0, 1, (7, 9, 21, 22), cream)
    _rect(draw, 0, 1, (42, 9, 56, 22), cream)
    _rect(draw, 0, 1, (13, 20, 21, 28), black)
    _rect(draw, 0, 1, (43, 20, 51, 28), black)
    _rect(draw, 0, 1, (12, 39, 52, 59), pink)
    _rect(draw, 0, 1, (18, 46, 25, 54), dark)
    _rect(draw, 0, 1, (39, 46, 46, 54), dark)
    _rect(draw, 1, 1, (7, 8, 25, 27), cream)
    _rect(draw, 2, 1, (18, 6, 45, 24), cream)
    _rect(draw, 3, 1, (39, 8, 57, 27), cream)

    # Legs use four directional tiles, with a consistent dark hoof at the bottom.
    for column in range(4):
        _rect(draw, column, 2, (0, 48, 63, 63), black)
        _rect(draw, column, 2, (8 + column * 3, 10, 28 + column * 3, 31), cream)

    # Top, bottom, ears, and tail.
    _rect(draw, 0, 3, (8, 8, 31, 29), cream)
    _rect(draw, 1, 3, (30, 22, 55, 47), cream)
    _rect(draw, 2, 3, (8, 17, 55, 45), (116, 78, 57))
    _rect(draw, 3, 3, (25, 4, 39, 55), (116, 78, 57))
    _rect(draw, 3, 3, (21, 48, 43, 63), black)
    return image


def _zombie_skin() -> Image.Image:
    image = Image.new("RGB", (SIZE, SIZE), (69, 88, 50))
    draw = ImageDraw.Draw(image)
    skin = (91, 112, 64)
    skin_dark = (61, 78, 44)
    cloth = (32, 105, 108)
    cloth_dark = (22, 69, 74)
    trousers = (38, 43, 55)
    black = (19, 24, 17)
    eye = (185, 190, 161)

    for column in range(4):
        _tile(draw, column, 0, skin)
        _tile(draw, column, 1, cloth)
        _tile(draw, column, 2, skin)
        _tile(draw, column, 3, trousers)

    # Head: recognizable front; sides and back intentionally contain no duplicated face.
    _rect(draw, 0, 0, (8, 10, 55, 18), skin_dark)
    _rect(draw, 0, 0, (10, 27, 25, 38), eye)
    _rect(draw, 0, 0, (39, 27, 54, 38), eye)
    _rect(draw, 0, 0, (14, 31, 25, 38), black)
    _rect(draw, 0, 0, (39, 31, 50, 38), black)
    _rect(draw, 0, 0, (20, 48, 44, 55), black)
    _rect(draw, 1, 0, (5, 12, 19, 32), skin_dark)
    _rect(draw, 1, 0, (35, 39, 58, 56), skin_dark)
    _rect(draw, 2, 0, (9, 8, 31, 29), skin_dark)
    _rect(draw, 2, 0, (38, 37, 59, 58), skin_dark)
    _rect(draw, 3, 0, (45, 12, 59, 32), skin_dark)
    _rect(draw, 3, 0, (6, 39, 29, 56), skin_dark)

    # Torso front/back/sides use stable garment seams.
    _rect(draw, 0, 1, (4, 5, 59, 13), cloth_dark)
    _rect(draw, 0, 1, (28, 8, 35, 59), cloth_dark)
    _rect(draw, 0, 1, (12, 34, 22, 43), (107, 83, 52))
    _rect(draw, 1, 1, (4, 7, 12, 58), cloth_dark)
    _rect(draw, 2, 1, (8, 8, 55, 17), cloth_dark)
    _rect(draw, 2, 1, (15, 35, 47, 52), (28, 83, 84))
    _rect(draw, 3, 1, (51, 7, 59, 58), cloth_dark)

    # Arms: skin hands at the bottom and directional sleeve seams.
    for column in range(4):
        _rect(draw, column, 2, (0, 0, 63, 39), cloth)
        _rect(draw, column, 2, (0, 0, 63, 8), cloth_dark)
        _rect(draw, column, 2, (0, 48, 63, 63), skin_dark)
    _rect(draw, 0, 2, (27, 10, 36, 39), cloth_dark)
    _rect(draw, 1, 2, (5, 9, 13, 39), cloth_dark)
    _rect(draw, 2, 2, (28, 10, 35, 39), (28, 83, 84))
    _rect(draw, 3, 2, (51, 9, 59, 39), cloth_dark)

    # Legs: four non-facial trouser faces and dark shoes.
    for column in range(4):
        _rect(draw, column, 3, (0, 49, 63, 63), (24, 27, 31))
    _rect(draw, 0, 3, (26, 4, 37, 48), (28, 31, 42))
    _rect(draw, 1, 3, (4, 5, 12, 48), (28, 31, 42))
    _rect(draw, 2, 3, (27, 4, 36, 48), (48, 52, 64))
    _rect(draw, 3, 3, (51, 5, 59, 48), (28, 31, 42))
    return image


def _player_skin() -> Image.Image:
    image = Image.new("RGB", (SIZE, SIZE), (105, 76, 58))
    draw = ImageDraw.Draw(image)
    skin = (178, 128, 92)
    skin_shadow = (138, 91, 68)
    hair = (48, 34, 31)
    eye = (52, 92, 122)
    shirt = (42, 112, 132)
    shirt_dark = (29, 77, 94)
    trousers = (48, 54, 78)
    boots = (31, 29, 34)

    for column in range(4):
        _tile(draw, column, 0, skin)
        _tile(draw, column, 1, shirt)
        _tile(draw, column, 2, shirt)
        _tile(draw, column, 3, trousers)

    # Face exists only on the authored front tile.
    _rect(draw, 0, 0, (5, 5, 58, 17), hair)
    _rect(draw, 0, 0, (7, 13, 15, 35), hair)
    _rect(draw, 0, 0, (49, 13, 57, 30), hair)
    _rect(draw, 0, 0, (15, 28, 23, 35), eye)
    _rect(draw, 0, 0, (41, 28, 49, 35), eye)
    _rect(draw, 0, 0, (27, 46, 38, 50), skin_shadow)
    _rect(draw, 1, 0, (5, 5, 18, 42), hair)
    _rect(draw, 2, 0, (4, 4, 59, 43), hair)
    _rect(draw, 3, 0, (46, 5, 59, 42), hair)

    # Jacket front/back and clean side seams.
    _rect(draw, 0, 1, (27, 4, 36, 59), shirt_dark)
    _rect(draw, 0, 1, (8, 8, 55, 15), (63, 142, 154))
    _rect(draw, 1, 1, (4, 4, 12, 59), shirt_dark)
    _rect(draw, 2, 1, (7, 7, 56, 16), shirt_dark)
    _rect(draw, 3, 1, (51, 4, 59, 59), shirt_dark)

    # Sleeves with hands at the authored lower edge.
    for column in range(4):
        _rect(draw, column, 2, (0, 0, 63, 45), shirt)
        _rect(draw, column, 2, (0, 0, 63, 8), shirt_dark)
        _rect(draw, column, 2, (0, 48, 63, 63), skin)

    # Trousers and boots.
    for column in range(4):
        _rect(draw, column, 3, (0, 49, 63, 63), boots)
    _rect(draw, 0, 3, (27, 4, 36, 48), (38, 42, 65))
    _rect(draw, 2, 3, (10, 7, 53, 16), (61, 66, 91))
    return image


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _cow_skin().save(OUTPUT / "cow-skin.png")
    _zombie_skin().save(OUTPUT / "zombie-skin.png")
    _player_skin().save(OUTPUT / "player-skin.png")


if __name__ == "__main__":
    main()
