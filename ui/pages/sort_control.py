from PySide6 import QtWidgets, QtCore


class SortControlWidget(QtWidgets.QWidget):
    """Виджет для управления сортировкой таблиц"""
    
    # Сигнал, который будет вызываться при изменении режима сортировки
    sortChanged = QtCore.Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Создаем layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем группу радиокнопок
        self.group = QtWidgets.QButtonGroup(self)
        
        # Радиокнопка для сортировки по дате
        self.date_sort = QtWidgets.QRadioButton("По дате")
        self.date_sort.setChecked(True)  # По умолчанию выбрана сортировка по дате
        self.group.addButton(self.date_sort)
        layout.addWidget(self.date_sort)
        
        # Радиокнопка для сортировки по коду
        self.code_sort = QtWidgets.QRadioButton("По коду")
        self.group.addButton(self.code_sort)
        layout.addWidget(self.code_sort)
        
        # Добавляем растягивающийся элемент для выравнивания
        layout.addStretch()
        
        # Подключаем сигналы
        self.date_sort.toggled.connect(self._on_sort_changed)
        self.code_sort.toggled.connect(self._on_sort_changed)
    
    def _on_sort_changed(self, checked):
        """Обработчик изменения режима сортировки"""
        if checked:
            # Испускаем сигнал с флагом, указывающим, выбрана ли сортировка по коду
            self.sortChanged.emit(self.code_sort.isChecked())
    
    def get_sort_by_code(self):
        """Получить текущий режим сортировки"""
        return self.code_sort.isChecked()
    
    def set_sort_by_code(self, sort_by_code):
        """Установить режим сортировки"""
        if sort_by_code:
            self.code_sort.setChecked(True)
        else:
            self.date_sort.setChecked(True)
