from __future__ import annotations

from .widgets import Panel
from .theme import VEILSTONE_THEME, UiTheme


class VBox(Panel):
    def __init__(
        self,
        theme: UiTheme = VEILSTONE_THEME,
        spacing: int | None = None,
        alignment: str = "center",
    ):
        super().__init__(theme)
        self.spacing = spacing if spacing is not None else theme.spacing
        self.alignment = alignment

    def layout(self, x: int, y: int, width: int, height: int) -> None:
        super().layout(x, y, width, height)
        if not self.children:
            return

        total_child_height = sum(c.bounds.height for c in self.children) + self.spacing * (
            len(self.children) - 1
        )

        # Start placing from the top, moving downwards. (In Pyglet, Y is up, so top is higher Y)
        # We center the whole block vertically by default if it fits
        current_y = y + (height + total_child_height) // 2

        for child in self.children:
            child_width = child.bounds.width if child.bounds.width > 0 else self.theme.button_width
            child_height = (
                child.bounds.height if child.bounds.height > 0 else self.theme.button_height
            )

            # Top-left of the child should be placed at current_y, so its bottom Y is current_y - child_height
            child_y = current_y - child_height

            if self.alignment == "center":
                child_x = x + (width - child_width) // 2
            elif self.alignment == "left":
                child_x = x + self.theme.panel_padding
            else:  # right
                child_x = x + width - child_width - self.theme.panel_padding

            child.layout(child_x, child_y, child_width, child_height)
            current_y -= child_height + self.spacing


class HBox(Panel):
    def __init__(
        self,
        theme: UiTheme = VEILSTONE_THEME,
        spacing: int | None = None,
        alignment: str = "center",
    ):
        super().__init__(theme)
        self.spacing = spacing if spacing is not None else theme.spacing
        self.alignment = alignment

    def layout(self, x: int, y: int, width: int, height: int) -> None:
        super().layout(x, y, width, height)
        if not self.children:
            return

        total_child_width = sum(c.bounds.width for c in self.children) + self.spacing * (
            len(self.children) - 1
        )

        # Start placing from the left, moving right
        if self.alignment == "center":
            current_x = x + (width - total_child_width) // 2
        elif self.alignment == "left":
            current_x = x + self.theme.panel_padding
        else:  # right
            current_x = x + width - total_child_width - self.theme.panel_padding

        for child in self.children:
            child_width = child.bounds.width if child.bounds.width > 0 else self.theme.button_width
            child_height = (
                child.bounds.height if child.bounds.height > 0 else self.theme.button_height
            )

            child_y = y + (height - child_height) // 2

            child.layout(current_x, child_y, child_width, child_height)
            current_x += child_width + self.spacing
