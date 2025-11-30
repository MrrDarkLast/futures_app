from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt
from db import SessionLocal
from models import Trade, Expiration


class FuturesCodeComboBox(QtWidgets.QWidget):
    """Собственная реализация комбобокса для кодов фьючерсов"""
    
    # Кастомный сигнал для изменения текста
    textChanged = QtCore.Signal(str)
    
    def __init__(self, parent=None, initial_code="", auto_generate_from_date=None, sorted_codes=None):
        super().__init__(parent)
        
        self.sorted_codes = sorted_codes
        
        # Создаем основной горизонтальный layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Создаем текстовое поле для ввода с автодополнением
        self.line_edit = QtWidgets.QLineEdit(self)
        self.line_edit.setPlaceholderText("Введите код фьючерса (FUSD_MM_YY)")
        
        # Настраиваем автодополнение
        self.completer = QtWidgets.QCompleter(self)
        self.completer_model = QStandardItemModel(self)
        self.completer.setModel(self.completer_model)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.line_edit.setCompleter(self.completer)
        
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
        self.popup_menu.setWindowFlags(
            QtCore.Qt.WindowType.Popup | 
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Загружаем существующие коды и заполняем меню
        self.futures_codes = []
        self.load_codes()
        
        # Связываем кнопку с выпадающим меню
        self.button.clicked.connect(self.show_popup)
        
        # Связываем сигнал изменения текста с внешним сигналом и автодополнением
        self.line_edit.textChanged.connect(self.textChanged)
        self.line_edit.textChanged.connect(self.on_text_changed)
        
        # Добавляем обработчик событий для дополнительного автодополнения
        self.line_edit.installEventFilter(self)
        
        # Добавляем подсказку о формате кода
        self.line_edit.setToolTip("Формат кода фьючерса: FUSD_MM_YY\nГде MM - месяц (01-12), YY - год (например, 96, 97)")
        
        # Устанавливаем начальное значение
        if initial_code:
            self.line_edit.setText(initial_code)
        elif auto_generate_from_date:
            # Автоматически генерируем код на основе даты
            generated_code = self.generate_code_from_date(auto_generate_from_date)
            self.line_edit.setText(generated_code)
            
    def load_codes(self):
        """Загружаем коды фьючерсов и создаем действия в меню"""
        # Очищаем меню перед заполнением
        self.popup_menu.clear()
        self.completer_model.clear()
        self.futures_codes = []
        
        if self.sorted_codes:
            self.futures_codes = self.sorted_codes.copy()
        else:
            try:
                with SessionLocal() as s:
                    codes = s.query(Expiration.future_code).distinct().all()
                    self.futures_codes = [code[0] for code in codes if code[0].startswith('FUSD_')]
                    self.futures_codes.sort()
            except Exception as e:
                pass
        
        # Добавляем коды в меню выбора
        for code in self.futures_codes:
            action = QAction(code, self)
            action.triggered.connect(lambda checked=False, c=code: self.select_code(c))
            self.popup_menu.addAction(action)
            
            # Добавляем в модель автодополнения
            item = QStandardItem(code)
            item.setToolTip(f"Код фьючерса: {code}")
            self.completer_model.appendRow(item)
        
        # Создаем группы кодов по месяцам и годам для контекстных подсказок
        self._create_code_groups()
            
    def _create_code_groups(self):
        """Создаем группы кодов по месяцам и годам для контекстных подсказок"""
        self.months = set()
        self.years = set()
        
        for code in self.futures_codes:
            parts = code.split('_')
            if len(parts) == 3:
                self.months.add(parts[1])
                self.years.add(parts[2])
            
    def show_popup(self):
        """Показывает выпадающее меню с кодами"""
        # Рассчитываем позицию меню под полем ввода
        button_rect = self.button.geometry()
        pos = self.mapToGlobal(QtCore.QPoint(button_rect.left(), button_rect.bottom() + 2))
        self.popup_menu.popup(pos)
        
    def select_code(self, code):
        """Устанавливает выбранный код в поле ввода"""
        self.line_edit.setText(code)
        # Устанавливаем курсор в конец строки
        self.line_edit.setCursorPosition(len(code))
        # Фокусируемся на поле ввода
        self.line_edit.setFocus()
    
    def on_text_changed(self, text):
        """Обработка изменения текста для интеллектуального дополнения"""
        if not text or len(text) < 3:
            return
            
        # Для существующих кодов предлагаем только точные соответствия
        suggestions = []
        
        # Если текст соответствует началу формата FUSD_
        if text.startswith("FUSD_"):
            parts = text.split('_')
            
            # Если введена первая часть FUSD_
            if len(parts) == 2:
                # Если уже начат ввод месяца
                if len(parts[1]) > 0:
                    # Ищем подходящие месяцы
                    month_prefix = parts[1]
                    for month in self.months:
                        if month.startswith(month_prefix):
                            suggestions.append(f"FUSD_{month}_")
            
            # Если введена вторая часть FUSD_MM_
            elif len(parts) == 3:
                month = parts[1]
                # Если уже начат ввод года
                if len(parts[2]) > 0:
                    # Ищем подходящие годы
                    year_prefix = parts[2]
                    for year in self.years:
                        if year.startswith(year_prefix):
                            suggestions.append(f"FUSD_{month}_{year}")
        
        # Если нашли точное соответствие в существующих кодах
        for code in self.futures_codes:
            if code.startswith(text) and code != text:
                # Приоритет существующим точным кодам
                suggestions.insert(0, code)
                break

    def eventFilter(self, obj, event):
        """Фильтр событий для обработки клавиш и интеллектуального дополнения"""
        if obj == self.line_edit and event.type() == QtCore.QEvent.KeyPress:
            text = self.line_edit.text()
            
            # Обработка нажатия Tab для автодополнения
            if event.key() == QtCore.Qt.Key_Tab:
                # Сначала пытаемся найти подходящий код из существующих
                if text:
                    for code in self.futures_codes:
                        if code.startswith(text) and code != text:
                            self.line_edit.setText(code)
                            self.line_edit.setCursorPosition(len(code))
                            return True  # Событие обработано
                    
                    # Если не нашли точного соответствия, пробуем интеллектуальное дополнение формата
                    if text.startswith("FUSD_"):
                        parts = text.split('_')
                        
                        # Дополнение месяца
                        if len(parts) == 2 and parts[1] and len(parts[1]) < 2:
                            # Например, FUSD_1 -> FUSD_01
                            if parts[1].isdigit() and 1 <= int(parts[1]) <= 9:
                                new_text = f"FUSD_0{parts[1]}_"
                                self.line_edit.setText(new_text)
                                self.line_edit.setCursorPosition(len(new_text))
                                return True
            
            # Подсказка для формата фьючерса при набивании F или FU
            if text == "F" or text == "FU":
                self.completer.setCompletionPrefix("FUSD_")
                self.completer.complete()
                return True
            
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
        
    def focusInEvent(self, event):
        """Обработка получения фокуса"""
        super().focusInEvent(event)
        
        # Показываем подсказку о формате при получении фокуса
        tip = "Формат кода: FUSD_MM_YY\n"
        
        # Добавляем примеры существующих кодов
        if self.futures_codes:
            tip += "\nПримеры кодов:\n"
            for i, code in enumerate(self.futures_codes[:5]):
                tip += f"• {code}\n"
            
            if len(self.futures_codes) > 5:
                tip += "..."
                
            # Создаем всплывающую подсказку
            QtWidgets.QToolTip.showText(
                self.mapToGlobal(QtCore.QPoint(0, self.height())), 
                tip, 
                self,
                self.rect(),
                2000  # Показываем на 2 секунды
            )
    
    def generate_code_from_date(self, date_obj):
        """Генерирует код FUSD_MM_YY на основе даты"""
        if hasattr(date_obj, 'toPython'):
            # Если это QDate
            date_obj = date_obj.toPython()
        
        month = f"{date_obj.month:02d}"
        year = f"{date_obj.year % 100:02d}"
        return f"FUSD_{month}_{year}"
    
    def update_code_from_date(self, date_obj):
        """Обновляет код на основе новой даты"""
        new_code = self.generate_code_from_date(date_obj)
        self.line_edit.setText(new_code)


class CustomDateEdit(QtWidgets.QWidget):
    dateChanged = QtCore.Signal(QtCore.QDate)
    
    def __init__(self, initial_date=None, parent=None):
        super().__init__(parent)
        self._date = initial_date if initial_date else None
        self._block_signals = False
        self._last_text = ""
        
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        self.line_edit = QtWidgets.QLineEdit(self)
        self.line_edit.setPlaceholderText("дд/мм/гггг")
        self.line_edit.setMaxLength(10)
        self.line_edit.setClearButtonEnabled(True)
        
        if self._date:
            self._last_text = self._date.toString("dd/MM/yyyy")
            self.line_edit.setText(self._last_text)
        
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.editingFinished.connect(self._on_editing_finished)
        
        self.calendar_button = QtWidgets.QToolButton(self)
        self.calendar_button.setText("📅")
        self.calendar_button.setToolTip("Выбрать дату из календаря")
        self.calendar_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.calendar_button.clicked.connect(self._show_calendar)
        
        layout.addWidget(self.line_edit)
        layout.addWidget(self.calendar_button)
        
        self.calendar = QtWidgets.QCalendarWidget()
        self.calendar.setWindowFlags(QtCore.Qt.WindowType.Popup | QtCore.Qt.WindowType.FramelessWindowHint)
        self.calendar.clicked.connect(self._calendar_date_selected)
        self.calendar.hide()
    
    def _show_calendar(self):
        if self._date and self._date.isValid():
            self.calendar.setSelectedDate(self._date)
        else:
            self.calendar.setSelectedDate(QtCore.QDate.currentDate())
        
        pos = self.mapToGlobal(QtCore.QPoint(0, self.height()))
        self.calendar.move(pos)
        self.calendar.show()
        self.calendar.setFocus()
    
    def _calendar_date_selected(self, qdate):
        self._date = qdate
        self._block_signals = True
        formatted = qdate.toString("dd/MM/yyyy")
        self.line_edit.setText(formatted)
        self._last_text = formatted
        self._block_signals = False
        self.calendar.hide()
        self.dateChanged.emit(qdate)
    
    def _on_text_changed(self, text):
        if self._block_signals:
            return
        
        if not text.strip():
            self._date = None
            self._last_text = ""
            return
        
        self._block_signals = True
        cursor_pos = self.line_edit.cursorPosition()
        
        clean_old = ''.join(c for c in self._last_text if c.isdigit())
        clean_new = ''.join(c for c in text if c.isdigit())
        
        formatted = ""
        for i, char in enumerate(clean_new):
            if i == 2 or i == 4:
                formatted += "/"
            formatted += char
        
        self.line_edit.setText(formatted)
        
        if len(clean_new) > len(clean_old):
            added_count = len(clean_new) - len(clean_old)
            if added_count == 1:
                if len(clean_new) == 2:
                    cursor_pos = 3
                elif len(clean_new) == 3:
                    cursor_pos = 4
                elif len(clean_new) == 4:
                    cursor_pos = 6
                elif len(clean_new) == 5:
                    cursor_pos = 7
                else:
                    cursor_pos = min(cursor_pos, len(formatted))
            else:
                cursor_pos = len(formatted)
        else:
            cursor_pos = min(cursor_pos, len(formatted))
        
        self.line_edit.setCursorPosition(cursor_pos)
        self._last_text = formatted
        self._block_signals = False
        
        self._try_parse_date(formatted)
    
    def _try_parse_date(self, text):
        if not text or len(text) < 10:
            if len(text) == 0:
                self._date = None
            return
        
        parts = text.split('/')
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if len(parts[2]) == 4:
                qdate = QtCore.QDate(year, month, day)
                if qdate.isValid():
                    if self._date != qdate:
                        self._date = qdate
                        self.dateChanged.emit(qdate)
                    return
                else:
                    self._date = None
                    return
        
        if len(text) == 10:
            self._date = None
    
    def _on_editing_finished(self):
        text = self.line_edit.text().strip()
        if not text:
            self._date = None
            return
        
        self._try_parse_date(text)
    
    def date(self):
        if self._date and self._date.isValid():
            return self._date
        return QtCore.QDate()
    
    def setDate(self, date_value):
        if date_value is None:
            self._date = None
            self._block_signals = True
            self.line_edit.clear()
            self._last_text = ""
            self._block_signals = False
            return
        
        if isinstance(date_value, QtCore.QDate):
            qdate = date_value
        else:
            from datetime import date as pydate
            if isinstance(date_value, pydate):
                qdate = QtCore.QDate(date_value.year, date_value.month, date_value.day)
            else:
                return
        
        if qdate.isValid():
            old_date = self._date
            self._date = qdate
            self._block_signals = True
            formatted = qdate.toString("dd/MM/yyyy")
            self.line_edit.setText(formatted)
            self._last_text = formatted
            self._block_signals = False
            
            if old_date != qdate:
                self.dateChanged.emit(qdate)
    
    def setCalendarPopup(self, enable):
        self.calendar_button.setVisible(enable)
    
    def setDisplayFormat(self, fmt):
        pass
    
    def setButtonSymbols(self, symbols):
        pass


def setup_date_edit(date_edit: QtWidgets.QDateEdit, placeholder: str = "дд/мм/гггг"):
    date_edit.setCalendarPopup(True)
    date_edit.setDisplayFormat("dd/MM/yyyy")
    date_edit.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)


class ToastNotification(QtWidgets.QWidget):
    """Всплывающее уведомление в стиле toast"""
    
    def __init__(self, message, parent=None, success=True):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        if success:
            icon_text = "✓"
            icon_color = "#4CAF50"
        else:
            icon_text = "✗"
            icon_color = "#F44336"
        
        self.setStyleSheet("""
            ToastNotification {
                background-color: transparent;
            }
        """)
        
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        frame = QtWidgets.QFrame(self)
        frame.setObjectName("toastFrame")
        frame.setStyleSheet("""
            QFrame#toastFrame {
                background-color: white;
                border-radius: 8px;
                border: 2px solid #e0e0e0;
            }
            QFrame#toastFrame QLabel {
                border: none;
                background: transparent;
            }
        """)
        
        layout = QtWidgets.QHBoxLayout(frame)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(16)
        
        icon_label = QtWidgets.QLabel(icon_text)
        icon_label.setStyleSheet(f"color: {icon_color}; font-size: 28px; font-weight: bold; background: transparent; border: none;")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        message_label = QtWidgets.QLabel(message)
        message_label.setStyleSheet("color: #333333; font-size: 16px; background: transparent; border: none;")
        message_label.setWordWrap(True)
        message_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        layout.addWidget(message_label, 1)
        
        main_layout.addWidget(frame)
        
        self.setMinimumWidth(350)
        self.setMaximumWidth(600)
        self.adjustSize()
        
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_in_animation = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        
        self.fade_out_animation = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(300)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QtCore.QEasingCurve.Type.InCubic)
        self.fade_out_animation.finished.connect(self.close)
        
    def show_toast(self):
        """Показать уведомление с автоматическим исчезновением"""
        if self.parent():
            parent_rect = self.parent().rect()
            parent_pos = self.parent().mapToGlobal(QtCore.QPoint(0, 0))
            x = parent_pos.x() + parent_rect.width() - self.width() - 20
            y = parent_pos.y() + parent_rect.height() - self.height() - 20
            self.move(x, y)
        
        self.show()
        self.raise_()
        self.fade_in_animation.start()
        
        QtCore.QTimer.singleShot(2500, self._start_fade_out)
    
    def _start_fade_out(self):
        """Начать анимацию исчезновения"""
        self.fade_out_animation.start()


def show_success_toast(parent, message):
    """Показать успешное уведомление"""
    toast = ToastNotification(message, parent, success=True)
    toast.show_toast()
    return toast


def show_error_toast(parent, message):
    """Показать уведомление об ошибке"""
    toast = ToastNotification(message, parent, success=False)
    toast.show_toast()
    return toast