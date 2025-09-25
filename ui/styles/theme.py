from PySide6 import QtWidgets, QtGui, QtCore


def apply_light_theme(app: QtWidgets.QApplication) -> None:
    """Применить светлую тему к приложению"""
    
    # Управляемый стиль
    app.setStyle("Fusion")

    # Светлая палитра
    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.Window, QtCore.Qt.white)
    pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.black)
    pal.setColor(QtGui.QPalette.Base, QtCore.Qt.white)
    pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#fafafa"))
    pal.setColor(QtGui.QPalette.Text, QtCore.Qt.black)
    pal.setColor(QtGui.QPalette.Button, QtCore.Qt.white)
    pal.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.black)
    pal.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
    pal.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.black)
    pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#d0e7ff"))
    pal.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
    app.setPalette(pal)

    # Нежный стиль для таблиц/заголовков/выделений
    app.setStyleSheet("""
        QMainWindow, QWidget { background: #ffffff; color: #000000; }
        QToolBar { background: #ffffff; border: none; }
        QTableView { 
            gridline-color: #dddddd;
            selection-background-color: #d0e7ff; 
            selection-color: #000000;
        }
        QHeaderView::section {
            background: #f5f5f5;
            color: #000000;
            font-weight: 600;
            padding: 6px 8px;
            border: 1px solid #e5e5e5;
        }
        QLineEdit, QComboBox, QDateEdit, QTextEdit {
            background: #ffffff;
            border: 1px solid #dcdcdc;
            padding: 4px 6px;
        }
        QPushButton {
            background-color: #f5f5f5 !important;
            border: 2px solid #999999;
            border-radius: 4px;
            padding: 6px 10px;
            color: #000000;
            font-weight: 500;
        }
        QPushButton:hover { 
            border-color: #666666; 
            background-color: #e8e8e8 !important;
            border-width: 2px;
        }
        QPushButton:pressed { 
            background-color: #e0e0e0 !important;
            border-color: #333333;
        }
        QToolBar {
            background: #ffffff;
            border: none;
            spacing: 3px;
        }
        QToolBar QToolButton {
            background-color: #f5f5f5 !important;
            border: 2px solid #999999 !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
            margin: 2px !important;
            font-weight: 600 !important;
            color: #000000 !important;
        }
        QToolBar QToolButton:hover {
            background-color: #e8e8e8 !important;
            border-color: #666666 !important;
            border-width: 2px !important;
        }
        QToolBar QToolButton:pressed {
            background-color: #e0e0e0 !important;
            border-color: #333333 !important;
        }
    """)

