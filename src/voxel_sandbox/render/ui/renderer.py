from collections.abc import Callable
from typing import Any

import pyglet

from .layout import HBox, VBox
from .menu import MenuController, Screen
from .theme import VEILSTONE_THEME
from .widgets import Button, Label, Panel, WorldCard


class UiRenderer:
    def __init__(self, window_width: int, window_height: int):
        self.batch = pyglet.graphics.Batch()
        self.width = window_width
        self.height = window_height

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

        self.world_cards: list[WorldCard] = []
        self.world_list_vbox = VBox(theme=VEILSTONE_THEME, spacing=8)
        self.world_actions_hbox1 = HBox(theme=VEILSTONE_THEME, spacing=16)
        self.world_actions_hbox2 = HBox(theme=VEILSTONE_THEME, spacing=16)

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._layout()

    def update(
        self,
        menu: MenuController,
        get_item_label: Callable[[int], str] | None = None,
        on_item_click: Callable[[int], None] | None = None,
        on_item_hover: Callable[[], None] | None = None,
    ) -> None:
        if self._current_screen != menu.screen or self._current_items != menu.items:
            self._current_screen = menu.screen
            self._current_items = menu.items
            self._rebuild_tree(menu, on_item_click, on_item_hover)

        if self._selected_index != menu.selected_index:
            self._selected_index = menu.selected_index
            for i, btn in enumerate(self.buttons):
                btn.hovered = i == self._selected_index

        self.title_label.text = menu.title
        self.status_label.text = menu.status

        for i, btn in enumerate(self.buttons):
            if i < len(menu.items):
                btn.text = get_item_label(i) if get_item_label else menu.items[i].label

    def update_world_list(
        self,
        worlds: list[tuple[str, Any]],
        selected_index: int,
        on_select: Callable[[int], None],
        on_play: Callable[[], None],
        on_create: Callable[[], None],
        on_edit: Callable[[], None],
        on_delete: Callable[[], None],
        on_cancel: Callable[[], None],
    ) -> None:
        if len(self.world_cards) != len(worlds) or any(
            c.name != w[0] for c, w in zip(self.world_cards, worlds, strict=False)
        ):
            self.batch = pyglet.graphics.Batch()
            self.world_cards.clear()
            self.world_list_vbox.children.clear()
            for i, w in enumerate(worlds):

                def make_cb(idx=i):
                    def cb():
                        on_select(idx)

                    return cb

                card = WorldCard(w[0])
                card.on_click = make_cb()
                self.world_cards.append(card)
                self.world_list_vbox.add_child(card)

            self.world_actions_hbox1.children.clear()
            self.world_actions_hbox1.add_child(Button("Play Selected World", on_play))
            self.world_actions_hbox1.add_child(Button("Create New World", on_create))

            self.world_actions_hbox2.children.clear()
            self.world_actions_hbox2.add_child(Button("Edit", on_edit))
            self.world_actions_hbox2.add_child(Button("Delete", on_delete))
            self.world_actions_hbox2.add_child(Button("Cancel", on_cancel))

            self._layout()

        for i, card in enumerate(self.world_cards):
            card.is_selected = i == selected_index

        # Rebuild tree logic for singleplayer screen adds these to root panel
        if (
            self._current_screen == Screen.SINGLEPLAYER
            and self.world_list_vbox not in self.root_panel.children
        ):
            self.root_panel.add_child(self.world_list_vbox)
            self.root_panel.add_child(self.world_actions_hbox1)
            self.root_panel.add_child(self.world_actions_hbox2)

    def _rebuild_tree(
        self,
        menu: MenuController,
        on_item_click: Callable[[int], None] | None,
        on_item_hover: Callable[[], None] | None,
    ) -> None:
        self.batch = pyglet.graphics.Batch()
        self.root_panel.children.clear()
        self.vbox.children.clear()
        self.buttons.clear()

        # We always add common widgets to root_panel
        self.root_panel.add_child(self.title_label)
        self.root_panel.add_child(self.status_label)

        if menu.screen != Screen.SINGLEPLAYER:
            for i, _item in enumerate(menu.items):

                def make_callback(index: int = i) -> Callable[[], None]:
                    def cb():
                        if on_item_click:
                            on_item_click(index)

                    return cb

                def make_hover(index: int = i) -> Callable[[], None]:
                    def cb():
                        menu.select(index)
                        if on_item_hover is not None:
                            on_item_hover()

                    return cb

                btn = Button(text=_item.label, on_click_callback=make_callback())
                btn.on_hover = make_hover()
                self.buttons.append(btn)
                self.vbox.add_child(btn)

            self.root_panel.add_child(self.vbox)

        self._layout()

    def _layout(self) -> None:
        title_y = self.height * 3 // 4
        self.title_label.layout(0, title_y - 20, self.width, 40)
        self.status_label.layout(0, self.height // 4 - 20, self.width, 40)

        if self._current_screen == Screen.SINGLEPLAYER:
            list_y = 120
            list_height = self.height - 220
            self.world_list_vbox.layout(0, list_y, self.width, list_height)
            self.world_actions_hbox1.layout(0, 60, self.width, 50)
            self.world_actions_hbox2.layout(0, 10, self.width, 50)
        else:
            self.vbox.layout(0, 0, self.width, self.height)

    def draw(self) -> None:
        self.root_panel.draw(self.batch)
        self.batch.draw()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool:
        return self.root_panel.on_mouse_motion(x, y, dx, dy)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool:
        return self.root_panel.on_mouse_press(x, y, button, modifiers)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> bool:
        return self.root_panel.on_mouse_release(x, y, button, modifiers)
