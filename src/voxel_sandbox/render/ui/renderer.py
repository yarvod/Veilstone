import pyglet
from typing import Callable
from .menu import MenuController
from .widgets import Button, Label, Panel
from .layout import VBox
from .theme import VEILSTONE_THEME


class UiRenderer:
    def __init__(self, window_width: int, window_height: int):
        self.batch = pyglet.graphics.Batch()
        self.width = window_width
        self.height = window_height

        # We cache the UI tree for the current screen so we don't rebuild it every frame unless it changes
        self._current_screen = None
        self._current_items = None
        self._selected_index = -1
        self.root_panel = Panel(theme=VEILSTONE_THEME)

        self.title_label = Label(
            "", font_size=VEILSTONE_THEME.title_size, color=VEILSTONE_THEME.text_color
        )
        self.status_label = Label(
            "", font_size=VEILSTONE_THEME.body_size, color=VEILSTONE_THEME.muted_text_color
        )

        self.buttons: list[Button] = []
        self.vbox = VBox(theme=VEILSTONE_THEME, spacing=16)

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._layout()

    from typing import Callable

    def update(
        self,
        menu: MenuController,
        get_item_label: Callable[[int], str] | None = None,
        on_item_click: Callable[[int], None] | None = None,
    ) -> None:
        # Rebuild if items changed or screen changed
        if self._current_screen != menu.screen or self._current_items != menu.items:
            self._current_screen = menu.screen
            self._current_items = menu.items
            self._rebuild_tree(menu, on_item_click)

        # Update selection state
        if self._selected_index != menu.selected_index:
            self._selected_index = menu.selected_index
            for i, btn in enumerate(self.buttons):
                btn.hovered = i == self._selected_index

        # Update dynamic text
        self.title_label.text = menu.title
        self.status_label.text = menu.status

        # If any button text needs updating based on menu state (like settings), it happens here:
        for i, btn in enumerate(self.buttons):
            if i < len(menu.items):
                btn.text = get_item_label(i) if get_item_label else menu.items[i].label

    def _rebuild_tree(
        self, menu: MenuController, on_item_click: Callable[[int], None] | None
    ) -> None:
        self.root_panel.children.clear()
        self.vbox.children.clear()
        self.buttons.clear()

        for i, item in enumerate(menu.items):

            def make_callback(index: int = i) -> Callable[[], None]:
                def cb():
                    if on_item_click:
                        on_item_click(index)

                return cb

            btn = Button(text=item.label, on_click_callback=make_callback())
            self.buttons.append(btn)
            self.vbox.add_child(btn)

        self._layout()

    def _layout(self) -> None:
        # Lay out the title at the top
        title_y = self.height * 3 // 4
        self.title_label.layout(0, title_y - 20, self.width, 40)

        # Lay out the buttons
        self.vbox.layout(0, 0, self.width, self.height)

        # Lay out status
        self.status_label.layout(0, self.height // 4 - 20, self.width, 40)

    def draw(self) -> None:
        # Let widgets add themselves to batch
        self.title_label.draw()
        self.vbox.draw()
        self.status_label.draw()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> int | None:
        for i, btn in enumerate(self.buttons):
            if btn.contains(x, y):
                return i
        return None
