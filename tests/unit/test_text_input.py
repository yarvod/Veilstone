from __future__ import annotations

from voxel_sandbox.render.ui.text_input import TextInput, TextPurpose


def test_text_input_appends_printable_text_and_enforces_limit() -> None:
    field = TextInput(TextPurpose.NICKNAME, "Name", maximum_length=5)

    field.append("Veil\nstone")

    assert field.value == "Veils"
    assert field.display == "Name\n> Veils_"


def test_text_input_backspace_handles_empty_value() -> None:
    field = TextInput(TextPurpose.CHAT, "Chat", value="a")

    field.backspace()
    field.backspace()

    assert field.value == ""
