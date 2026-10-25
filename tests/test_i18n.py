"""Translations are complete, consistent, and actually used by every window."""

import ast
import json
import re
from pathlib import Path
from string import Formatter

import pytest

from aniccoli.filters import SortField
from aniccoli.i18n import LANGUAGES, TRANSLATIONS, choice_key, translate
from aniccoli.preferences import (
    AppPreferences,
    load_preferences,
    save_preferences,
    update_preferences,
)


PACKAGE = Path(__file__).parent.parent / "aniccoli"
WINDOW_MODULES = ("app.py", "audit_window.py", "duplicate_window.py", "statistics_window.py")


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(text) if name}


def test_every_language_has_every_key_with_the_same_placeholders() -> None:
    assert set(TRANSLATIONS) == set(LANGUAGES)
    english = TRANSLATIONS["en"]
    for language, table in TRANSLATIONS.items():
        assert set(table) == set(english), language
        for key, text in table.items():
            assert placeholders(text) == placeholders(english[key]), (language, key)


def test_translate_falls_back_to_english_then_to_the_key() -> None:
    assert translate("ja", "close") == "閉じる"
    assert translate("xx", "close") == "Close"
    assert translate("ja", "no_such_key") == "no_such_key"
    assert translate("en", "undo_failed", error="disk full") == "Undo failed: disk full"
    assert translate("en", "undo_failed") == "Undo failed: {error}"
    # A message may itself have a "language" value.
    assert translate("ms", "language_changed", language="日本語") == "Bahasa ditukar kepada 日本語."


def test_choice_keys() -> None:
    assert choice_key(SortField.SIZE) == "SortField.SIZE"
    assert choice_key("size_any") == "size_any"
    assert translate("zh", choice_key(SortField.SIZE)) == "文件大小"


def test_language_is_saved_with_the_other_preferences(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    save_preferences(update_preferences(AppPreferences(), language="ms"), path)

    assert json.loads(path.read_text())["language"] == "ms"
    assert load_preferences(path).language == "ms"


def test_language_from_the_old_language_file_is_picked_up(tmp_path: Path) -> None:
    (tmp_path / "ui_language.txt").write_text("zh\n")
    assert load_preferences(tmp_path / "preferences.json").language == "zh"

    (tmp_path / "preferences.json").write_text(json.dumps({"recursive_scan": False}))
    assert load_preferences(tmp_path / "preferences.json").language == "zh"

    (tmp_path / "ui_language.txt").write_text("klingon")
    assert load_preferences(tmp_path / "preferences.json").language == "en"


@pytest.mark.parametrize("module", WINDOW_MODULES)
def test_windows_show_no_untranslated_text(module: str) -> None:
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    untranslated = []

    for node in ast.walk(tree):
        if not (isinstance(node, ast.keyword) and node.arg in ("text", "title", "message")):
            continue
        parts = list(ast.walk(node.value))
        translated = any(
            isinstance(part, ast.Call) and getattr(part.func, "attr", getattr(part.func, "id", "")) in ("_t", "_label")
            for part in parts
        )
        words = [
            part.value
            for part in parts
            if isinstance(part, ast.Constant) and isinstance(part.value, str) and re.search("[A-Za-z]{2}", part.value)
        ]
        if words and not translated:
            untranslated.append((node.lineno, words[0]))

    assert untranslated == []
