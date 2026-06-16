from __future__ import annotations

import pyglet
from typing import Callable, Literal
from .geometry import Rect
from .theme import VEILSTONE_THEME, UiTheme


class Widget:
    def __init__(self, theme: UiTheme = VEILSTONE_THEME):
        self.theme = theme
        self.bounds = Rect(0, 0, 0, 0)
        self.visible = True
        self.enabled = True
        self.hovered = False
        self.pressed = False

    def contains(self, x: int, y: int) -> bool:
        return self.bounds.contains(x, y)

    def layout(self, x: int, y: int, width: int, height: int) -> None:
        self.bounds.x = x
        self.bounds.y = y
        self.bounds.width = width
        self.bounds.height = height

    def draw(
        self, batch: pyglet.graphics.Batch | None = None, group: pyglet.graphics.Group | None = None
    ) -> None:
        pass

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool:
        was_hovered = self.hovered
        self.hovered = self.contains(x, y)
        return self.hovered != was_hovered

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool:
        if self.contains(x, y) and self.enabled:
            self.pressed = True
            return True
        return False

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> bool:
        if self.pressed:
            self.pressed = False
            if self.contains(x, y) and self.enabled:
                self.on_click()
            return True
        return False

    def on_click(self) -> None:
        pass


class Label(Widget):
    def __init__(
        self,
        text: str,
        theme: UiTheme = VEILSTONE_THEME,
        font_size: int | None = None,
        color: tuple[int, int, int, int] | None = None,
        anchor_x: Literal["left", "center", "right"] = "center",
        anchor_y: Literal["top", "bottom", "center", "baseline"] = "center",
    ):
        super().__init__(theme)
        self._text = text
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y
        self.font_size = font_size or theme.body_size
        self.color = color or theme.text_color
        self._label = pyglet.text.Label(
            text,
            font_name=theme.font_name,
            font_size=self.font_size,
            color=self.color,
            anchor_x=anchor_x,
            anchor_y=anchor_y,
        )

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        if self._text != value:
            self._text = value
            self._label.text = value

    def layout(self, x: int, y: int, width: int, height: int) -> None:
        super().layout(x, y, width, height)
        # Position label based on anchor
        if self.anchor_x == "center":
            self._label.x = x + width // 2
        elif self.anchor_x == "left":
            self._label.x = x
        else:
            self._label.x = x + width

        if self.anchor_y == "center":
            self._label.y = y + height // 2
        elif self.anchor_y == "bottom":
            self._label.y = y
        else:
            self._label.y = y + height

    def draw(
        self, batch: pyglet.graphics.Batch | None = None, group: pyglet.graphics.Group | None = None
    ) -> None:
        if not self.visible:
            return
        if batch is not None:
            self._label.batch = batch
            if group is not None:
                self._label.group = group
        else:
            self._label.batch = None
            self._label.draw()


class Button(Widget):
    def __init__(
        self,
        text: str,
        on_click_callback: Callable[[], None] | None = None,
        theme: UiTheme = VEILSTONE_THEME,
    ):
        super().__init__(theme)
        self.on_click_callback = on_click_callback
        self.label = Label(text, theme=theme)
        self._rect = pyglet.shapes.BorderedRectangle(
            0,
            0,
            theme.button_width,
            theme.button_height,
            2,
            color=theme.button_color,
            border_color=theme.panel_border_color,
        )

    @property
    def text(self) -> str:
        return self.label.text

    @text.setter
    def text(self, value: str) -> None:
        self.label.text = value

    def layout(self, x: int, y: int, width: int, height: int) -> None:
        super().layout(x, y, width, height)
        self._rect.x = x
        self._rect.y = y
        self._rect.width = width
        self._rect.height = height
        self.label.layout(x, y, width, height)

    def draw(
        self, batch: pyglet.graphics.Batch | None = None, group: pyglet.graphics.Group | None = None
    ) -> None:
        if not self.visible:
            return

        if not self.enabled:
            self._rect.color = self.theme.background_color
            self.label.color = self.theme.muted_text_color
            self._rect.opacity = 128
        elif self.pressed:
            self._rect.color = self.theme.button_pressed_color
            self.label.color = self.theme.text_color
            self._rect.opacity = 255
        elif self.hovered:
            self._rect.color = self.theme.button_hover_color
            self.label.color = self.theme.accent_color
            self._rect.opacity = 255
        else:
            self._rect.color = self.theme.button_color
            self.label.color = self.theme.text_color
            self._rect.opacity = 255

        if batch is not None:
            self._rect.batch = batch
            if group is not None:
                self._rect.group = group
        else:
            self._rect.batch = None
            self._rect.draw()

        self.label.draw(batch, group)

    def on_click(self) -> None:
        if self.on_click_callback:
            self.on_click_callback()


class Panel(Widget):
    def __init__(self, theme: UiTheme = VEILSTONE_THEME):
        super().__init__(theme)
        self.children: list[Widget] = []
        self._bg = pyglet.shapes.BorderedRectangle(
            0, 0, 10, 10, 2, color=theme.panel_color, border_color=theme.panel_border_color
        )

    def add_child(self, child: Widget) -> None:
        self.children.append(child)

    def layout(self, x: int, y: int, width: int, height: int) -> None:
        super().layout(x, y, width, height)
        self._bg.x = x
        self._bg.y = y
        self._bg.width = width
        self._bg.height = height

    def draw(
        self, batch: pyglet.graphics.Batch | None = None, group: pyglet.graphics.Group | None = None
    ) -> None:
        if not self.visible:
            return
        if batch is not None:
            self._bg.batch = batch
            if group is not None:
                self._bg.group = group
        else:
            self._bg.batch = None
            self._bg.draw()

        # Simple layer management if drawing manually, otherwise rely on Pyglet Groups
        for child in self.children:
            child.draw(batch, group)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool:
        handled = False
        for child in reversed(self.children):
            if child.on_mouse_motion(x, y, dx, dy):
                handled = True
        return handled or super().on_mouse_motion(x, y, dx, dy)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool:
        for child in reversed(self.children):
            if child.on_mouse_press(x, y, button, modifiers):
                return True
        return super().on_mouse_press(x, y, button, modifiers)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> bool:
        for child in reversed(self.children):
            if child.on_mouse_release(x, y, button, modifiers):
                return True
        return super().on_mouse_release(x, y, button, modifiers)


class WorldCard(Widget):
    def __init__(self, name: str, is_selected: bool = False, theme: UiTheme = VEILSTONE_THEME):
        super().__init__(theme)
        self.name = name
        self.is_selected = is_selected
        self._rect = pyglet.shapes.BorderedRectangle(
            0,
            0,
            theme.button_width + 180,
            theme.button_height,
            2,
            color=theme.panel_color,
            border_color=theme.accent_color if is_selected else theme.panel_border_color,
        )
        self._label = Label(name, theme=theme, anchor_x="left")

    def layout(self, x: int, y: int, width: int, height: int) -> None:
        super().layout(x, y, width, height)
        self._rect.x = x
        self._rect.y = y
        self._rect.width = width
        self._rect.height = height
        self._label.layout(
            x + self.theme.panel_padding, y, width - self.theme.panel_padding * 2, height
        )

    def draw(
        self, batch: pyglet.graphics.Batch | None = None, group: pyglet.graphics.Group | None = None
    ) -> None:
        if not self.visible:
            return

        if self.is_selected:
            self._rect.border_color = self.theme.accent_color
            self._rect.opacity = 255
        elif self.hovered:
            self._rect.border_color = self.theme.button_hover_color
            self._rect.opacity = 255
        else:
            self._rect.border_color = self.theme.panel_border_color
            self._rect.opacity = 200

        if batch is not None:
            self._rect.batch = batch
            if group is not None:
                self._rect.group = group
        else:
            self._rect.batch = None
            self._rect.draw()

        self._label.draw(batch, group)
