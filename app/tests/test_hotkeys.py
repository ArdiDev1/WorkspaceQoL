import pytest
import win32con

from wlm.hotkeys import parse_hotkey


def test_parse_simple_combo():
    modifiers, vk = parse_hotkey("Ctrl+Alt+L")

    assert modifiers & win32con.MOD_CONTROL
    assert modifiers & win32con.MOD_ALT
    assert vk == ord("L")


def test_parse_is_case_insensitive_on_modifiers():
    modifiers, vk = parse_hotkey("ctrl+ALT+k")

    assert modifiers & win32con.MOD_CONTROL
    assert modifiers & win32con.MOD_ALT
    assert vk == ord("K")


def test_parse_accepts_digit_key():
    _, vk = parse_hotkey("Ctrl+1")

    assert vk == ord("1")


def test_parse_rejects_missing_modifier():
    with pytest.raises(ValueError):
        parse_hotkey("L")


def test_parse_rejects_unknown_modifier():
    with pytest.raises(ValueError):
        parse_hotkey("Foo+L")


def test_parse_rejects_multi_char_key():
    with pytest.raises(ValueError):
        parse_hotkey("Ctrl+Alt+Enter")


def test_parse_rejects_empty_string():
    with pytest.raises(ValueError):
        parse_hotkey("")
