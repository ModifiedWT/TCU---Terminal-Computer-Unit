"""
PDA Widget — a frameless, always-on-top desktop dashboard.
STALKER PDA-inspired: amber-on-dark, monospace, scanline texture.

Run with:  python main.py
"""

import sys
from PyQt6.QtWidgets import QApplication
from pda_window import PDAWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # native Windows style doesn't reliably honor
                             # QSS min/max-width on buttons, which was
                             # causing the visible icon and the actual
                             # clickable area to drift apart
    app.setQuitOnLastWindowClosed(False)  # tray icon controls lifetime now

    window = PDAWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()