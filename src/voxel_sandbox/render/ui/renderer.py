from collections.abc import Callable
from typing import Any

import pyglet

from .layout import HBox, VBox
from .menu import MenuController, Screen
from .theme import VEILSTONE_THEME
from .widgets import Button, Label, Panel, WorldCard

_LIST_SCREENS = {Screen.SINGLEPLAYER, Screen.TEXTURE_PACKS}


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

        # Persistent action buttons — preserved between frames so pressed state survives.
        self._action_primary = Button("", theme=VEILSTONE_THEME)
        self._action_secondary = Button("", theme=VEILSTONE_THEME)
        self._action_edit = Button("", theme=VEILSTONE_THEME)
        self._action_delete = Button("", theme=VEILSTONE_THEME)
        self._action_cancel = Button("", theme=VEILSTONE_THEME)

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
        *,
        primary_label: str = "Play Selected World",
        secondary_label: str = "Create New World",
        edit_label: str = "Edit",
        delete_label: str = "Delete",
        cancel_label: str = "Cancel",
    ) -> None:
        # Rebuild world card list only when its contents actually change.
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

        # Update persistent action buttons: update labels and callbacks without
        # recreating button objects, so the pressed state survives between frames.
        self._rebuild_action_row(
            self.world_actions_hbox1,
            [(primary_label, on_play), (secondary_label, on_create)],
            [self._action_primary, self._action_secondary],
        )
        self._rebuild_action_row(
            self.world_actions_hbox2,
            [(edit_label, on_edit), (delete_label, on_delete), (cancel_label, on_cancel)],
            [self._action_edit, self._action_delete, self._action_cancel],
        )

        for i, card in enumerate(self.world_cards):
            card.is_selected = i == selected_index

        # Add list widgets to root panel on first appearance.
        if (
            self._current_screen in _LIST_SCREENS
            and self.world_list_vbox not in self.root_panel.children
        ):
            self.root_panel.add_child(self.world_list_vbox)
            self.root_panel.add_child(self.world_actions_hbox1)
            self.root_panel.add_child(self.world_actions_hbox2)

        self._layout()

    def _rebuild_action_row(
        self,
        hbox: HBox,
        entries: list[tuple[str, Callable[[], None]]],
        pool: list[Button],
    ) -> None:
        hbox.children.clear()
        visible_count = 0
        for btn, (label, cb) in zip(pool, entries, strict=False):
            if not label:
                continue
            btn.text = label
            btn.on_click_callback = cb
            btn.visible = True
            hbox.add_child(btn)
            visible_count += 1
        for btn in pool[visible_count:]:
            btn.visible = False

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

        self.root_panel.add_child(self.title_label)
        self.root_panel.add_child(self.status_label)

        if menu.screen not in _LIST_SCREENS:
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

        if self._current_screen in _LIST_SCREENS:
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
