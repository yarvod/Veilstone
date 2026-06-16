from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UiTheme:
    font_name: str
    title_size: int
    body_size: int
    button_width: int
    button_height: int
    spacing: int
    panel_padding: int
    background_color: tuple[int, int, int, int]
    panel_color: tuple[int, int, int, int]
    panel_border_color: tuple[int, int, int, int]
    button_color: tuple[int, int, int, int]
    button_hover_color: tuple[int, int, int, int]
    button_pressed_color: tuple[int, int, int, int]
    text_color: tuple[int, int, int, int]
    muted_text_color: tuple[int, int, int, int]
    accent_color: tuple[int, int, int, int]


# Veilstone style: dark slate/stone, warm gold accent, soft borders
VEILSTONE_THEME = UiTheme(
    font_name="Minecraft",
    title_size=38,
    body_size=16,
    button_width=300,
    button_height=48,
    spacing=12,
    panel_padding=24,
    background_color=(15, 18, 25, 200),
    panel_color=(34, 38, 48, 255),
    panel_border_color=(132, 142, 158, 255),
    button_color=(45, 50, 65, 255),
    button_hover_color=(60, 68, 85, 255),
    button_pressed_color=(30, 35, 45, 255),
    text_color=(240, 245, 255, 255),
    muted_text_color=(170, 180, 200, 255),
    accent_color=(245, 220, 140, 255),
)
