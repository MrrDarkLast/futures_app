from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QAction

from ui.models.table_models import CombinedTableModel


class CombinedPage(QtWidgets.QWidget):
    """Третья: совмещённая таблица (read-only) + Обновить."""
    
    def __init__(self):
        super().__init__()
        self.model = CombinedTableModel()
        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)  # Включаем возможность сортировки
        self.view.horizontalHeader().setSortIndicator(0, QtCore.Qt.AscendingOrder)  # По умолчанию сортировка по дате торгов (возрастание)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().setStretchLastSection(True)

        # Удаляем тулбар, так как он содержал только кнопку "Обновить"
        v = QtWidgets.QVBoxLayout(self)
        v.addWidget(self.view)
