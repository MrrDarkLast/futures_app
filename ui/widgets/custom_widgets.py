from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtGui import QAction
from db import SessionLocal
from models import Trade


class FuturesCodeComboBox(QtWidgets.QWidget):
    """Собственная реализация комбобокса для кодов фьючерсов"""
    
    # Кастомный сигнал для изменения текста
    textChanged = QtCore.Signal(str)
    
    def __init__(self, parent=None, initial_code=""):
        super().__init__(parent)
        
        # Создаем основной горизонтальный layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Создаем текстовое поле для ввода
        self.line_edit = QtWidgets.QLineEdit(self)
        self.line_edit.setPlaceholderText("Введите код фьючерса (FUSD_MM_YY)")
        
        # Создаем кнопку для выпадающего списка
        self.button = QtWidgets.QToolButton(self)
        self.button.setText("▼")
        self.button.setFixedWidth(20)
        self.button.setCursor(QtCore.Qt.PointingHandCursor)
        
        # Добавляем виджеты в layout
        layout.addWidget(self.line_edit)
        layout.addWidget(self.button)
        
        # Создаем выпадающее меню
        self.popup_menu = QtWidgets.QMenu(self)
        
        # Загружаем существующие коды и заполняем меню
        self.load_codes()
        
        # Связываем кнопку с выпадающим меню
        self.button.clicked.connect(self.show_popup)
        
        # Связываем сигнал изменения текста с внешним сигналом
        self.line_edit.textChanged.connect(self.textChanged)
        
        # Добавляем обработчик событий для автодополнения
        self.line_edit.installEventFilter(self)
        
        # Устанавливаем начальное значение, если оно передано
        if initial_code:
            self.line_edit.setText(initial_code)
            
    def load_codes(self):
        """Загружаем коды фьючерсов и создаем действия в меню"""
        # Очищаем меню перед заполнением
        self.popup_menu.clear()
        
        # Пытаемся загрузить коды из базы данных
        try:
            with SessionLocal() as s:
                codes = s.query(Trade.future_code).distinct().all()
                futures_codes = [code[0] for code in codes if code[0].startswith('FUSD_')]
                futures_codes.sort()
                
                # Добавляем коды в меню
                for code in futures_codes:
                    action = QAction(code, self)
                    action.triggered.connect(lambda checked=False, c=code: self.select_code(c))
                    self.popup_menu.addAction(action)
                    
        except Exception as e:
            # Если произошла ошибка при загрузке, просто продолжаем
            pass
            
    def show_popup(self):
        """Показывает выпадающее меню с кодами"""
        # Рассчитываем позицию меню под полем ввода
        pos = self.line_edit.mapToGlobal(QtCore.QPoint(0, self.line_edit.height()))
        self.popup_menu.popup(pos)
        
    def select_code(self, code):
        """Устанавливает выбранный код в поле ввода"""
        self.line_edit.setText(code)
        # Устанавливаем курсор в конец строки
        self.line_edit.setCursorPosition(len(code))
        # Фокусируемся на поле ввода
        self.line_edit.setFocus()
    
    def eventFilter(self, obj, event):
        """Фильтр событий для обработки клавиш и автодополнения"""
        if obj == self.line_edit and event.type() == QtCore.QEvent.KeyPress:
            text = self.line_edit.text()
            
            # Если нажата клавиша Tab и текст начинается с FUSD
            if event.key() == QtCore.Qt.Key_Tab and text and text.startswith("FUSD"):
                # Попробуем найти подходящий код
                try:
                    with SessionLocal() as s:
                        codes = s.query(Trade.future_code).distinct().filter(
                            Trade.future_code.startswith(text)
                        ).all()
                        
                        if codes:
                            # Берем первый подходящий код
                            suggestion = codes[0][0]
                            if suggestion != text and suggestion.startswith(text):
                                self.line_edit.setText(suggestion)
                                self.line_edit.setCursorPosition(len(suggestion))
                                return True  # Событие обработано
                except:
                    pass
                    
        # Передаем событие дальше
        return super().eventFilter(obj, event)
            
    def text(self):
        """Возвращает текущий текст"""
        return self.line_edit.text()
        
    def setText(self, text):
        """Устанавливает текст в поле ввода"""
        self.line_edit.setText(text)
        
    def setCurrentText(self, text):
        """Совместимость с QComboBox API"""
        self.line_edit.setText(text)
        
    def currentText(self):
        """Совместимость с QComboBox API"""
        return self.line_edit.text()
        
    def get_clean_code(self):
        """Возвращает очищенный код фьючерса"""
        return self.line_edit.text().strip()