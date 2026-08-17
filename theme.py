"""
Theme definitions. Each theme is a dict of color values plugged into
the QSS template in style_template.qss. Add a new theme by adding a
new dict here — no QSS editing required.
"""

from string import Template
import os
import sys


def _resource_dir() -> str:
    """Returns the ui/ folder, whether running from source or a
    PyInstaller --onefile exe (which unpacks data files to a temp
    dir referenced by sys._MEIPASS at runtime)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "ui")
    return os.path.dirname(__file__)

THEMES = {
    "amber": {
        "bg": "rgba(12, 14, 10, 220)",
        "border": "rgba(140, 120, 60, 180)",
        "text": "#c9a94f",
        "text_bright": "#e8c766",
        "text_dim": "#7d7040",
        "header": "#e0b84a",
        "date": "#8a7a45",
        "bar_bg": "rgba(40, 36, 20, 200)",
        "bar_border": "rgba(140, 120, 60, 120)",
        "bar_chunk": "#a9822f",
    },
    "green": {  # classic phosphor terminal
        "bg": "rgba(8, 14, 10, 220)",
        "border": "rgba(60, 140, 80, 180)",
        "text": "#59c97a",
        "text_bright": "#7fe89c",
        "text_dim": "#3f7a52",
        "header": "#6fdb8e",
        "date": "#3f7a52",
        "bar_bg": "rgba(20, 40, 26, 200)",
        "bar_border": "rgba(60, 140, 80, 120)",
        "bar_chunk": "#3f9c5c",
    },
    "red": {  # alert / blood-red
        "bg": "rgba(16, 10, 10, 220)",
        "border": "rgba(160, 50, 50, 180)",
        "text": "#d16a6a",
        "text_bright": "#f08a8a",
        "text_dim": "#7a3f3f",
        "header": "#e57373",
        "date": "#7a3f3f",
        "bar_bg": "rgba(40, 20, 20, 200)",
        "bar_border": "rgba(160, 50, 50, 120)",
        "bar_chunk": "#a93a3a",
    },
    "blue": {  # EDITH-style HUD blue
        "bg": "rgba(8, 12, 16, 220)",
        "border": "rgba(60, 130, 190, 180)",
        "text": "#6fb8e0",
        "text_bright": "#8fd2f5",
        "text_dim": "#3f6d8a",
        "header": "#7cc4e8",
        "date": "#3f6d8a",
        "bar_bg": "rgba(18, 30, 40, 200)",
        "bar_border": "rgba(60, 130, 190, 120)",
        "bar_chunk": "#3a86c9",
    },
}

THEME_ORDER = ["amber", "green", "red", "blue"]


def build_stylesheet(theme_name: str) -> str:
    """Fills the QSS template with the given theme's colors."""
    template_path = os.path.join(_resource_dir(), "style_template.qss")
    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())
    return template.substitute(THEMES[theme_name])
