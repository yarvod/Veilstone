from __future__ import annotations

import pytest
from pyglet.window import mouse

from voxel_sandbox.render.ui.widgets import Button
from voxel_sandbox.render.ui.layout import VBox
from voxel_sandbox.render.ui.renderer import UiRenderer


def test_ui_button_hover_and_click():
    # Setup simple UI
    renderer = UiRenderer(800, 600)
    
    clicked = False
    def on_click():
        nonlocal clicked
        clicked = True
        
    btn = Button("Test Button", on_click_callback=on_click)
    # Button is sized by default to 240x48 in layout
    vbox = VBox()
    vbox.add_child(btn)
    
    # Layout the vbox on the screen
    # width=800, height=600. Center aligned.
    # Total child height = 48.
    # start_y = y + (height + total_child_height) // 2 = 0 + (600 + 48) // 2 = 324
    # child_y = 324 - 48 = 276
    # child_x = (800 - 300) // 2 = 250
    vbox.layout(0, 0, 800, 600)
    
    assert btn.bounds.x == 250
    assert btn.bounds.y == 276
    assert btn.bounds.width == 300
    assert btn.bounds.height == 48

    # Mouse motion OUTSIDE the button
    vbox.on_mouse_motion(0, 0, 0, 0)
    assert not btn.hovered
    
    # Mouse motion INSIDE the button
    vbox.on_mouse_motion(260, 280, 0, 0)
    assert btn.hovered

    # Right click inside the button shouldn't do anything (we added explicit guard)
    vbox.on_mouse_press(260, 280, mouse.RIGHT, 0)
    assert not btn.pressed

    # Left click inside the button
    vbox.on_mouse_press(260, 280, mouse.LEFT, 0)
    assert btn.pressed
    assert not clicked
    
    # Left release inside the button triggers click
    vbox.on_mouse_release(260, 280, mouse.LEFT, 0)
    assert not btn.pressed
    assert clicked

def test_ui_world_card_click():
    from voxel_sandbox.render.ui.widgets import WorldCard
    
    card = WorldCard("Test World")
    vbox = VBox()
    vbox.add_child(card)
    vbox.layout(0, 0, 800, 600)
    
    # Card is wider than standard button. width = 300 + 180 = 480.
    # child_x = (800 - 480) // 2 = 160
    assert card.bounds.width == 480
    assert card.bounds.x == 160
    
    # Click on the far right edge of the card (should be clickable since we fixed the bounds)
    card_right_x = 160 + 400
    
    # Needs a mock on_click handler
    clicked = False
    def on_click():
        nonlocal clicked
        clicked = True
        
    card.on_click = on_click
    
    vbox.on_mouse_press(card_right_x, 280, mouse.LEFT, 0)
    assert card.pressed
    
    vbox.on_mouse_release(card_right_x, 280, mouse.LEFT, 0)
    assert clicked
