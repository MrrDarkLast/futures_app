from __future__ import annotations

# --- bootstrap to allow absolute package imports when run as a script ---
import os, sys
if __package__ is None or __package__ == "":
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from PySide6 import QtWidgets

from services import init_db
from ui.main_window import MainWindow
from ui.styles.theme import apply_light_theme


def main():
    """Основная точка входа в приложение"""
    init_db()
    app = QtWidgets.QApplication([])
    apply_light_theme(app)
    w = MainWindow()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
