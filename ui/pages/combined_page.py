from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QAction, QPainter, QPen, QFont
from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from datetime import date

from db import SessionLocal
from ui.models.table_models import CombinedTableModel
from ui.widgets.custom_widgets import FuturesCodeComboBox, CustomDateEdit
from validators import FuturesValidator


class ArrowButton(QtWidgets.QPushButton):
    """Кнопка со стрелкой"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = True
        self.setFixedSize(24, 24)
        self.setText("")
        self.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
        """)
        self.setContentsMargins(0, 0, 0, 0)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QtCore.Qt.GlobalColor.darkGray, 0))
        painter.setBrush(QtCore.Qt.GlobalColor.darkGray)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        size = 5
        
        if self._expanded:
            points = [
                QtCore.QPointF(center_x, center_y + size),
                QtCore.QPointF(center_x - size, center_y - size // 2),
                QtCore.QPointF(center_x + size, center_y - size // 2)
            ]
        else:
            points = [
                QtCore.QPointF(center_x - size, center_y),
                QtCore.QPointF(center_x + size // 2, center_y - size),
                QtCore.QPointF(center_x + size // 2, center_y + size)
            ]
        
        painter.drawPolygon(points)
        
    def setExpanded(self, expanded):
        if self._expanded != expanded:
            self._expanded = expanded
            self.update()
    
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.parent().toggle()
        super().mousePressEvent(event)


class CollapsibleHeader(QtWidgets.QWidget):
    """Заголовок с кнопкой-стрелкой для сворачивания"""
    
    toggled = QtCore.Signal(bool)
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self._expanded = True
        self.setFixedHeight(32)
        
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.arrow_button = ArrowButton(self)
        
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #333333;")
        self.title_label.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        
        layout.addWidget(self.arrow_button)
        layout.addWidget(self.title_label)
        layout.addStretch()
        
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            CollapsibleHeader {
                border-radius: 4px;
                padding: 2px;
            }
            CollapsibleHeader:hover {
                background-color: #f0f0f0;
            }
        """)
        
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.toggle()
        super().mousePressEvent(event)
        
    def toggle(self):
        self._expanded = not self._expanded
        self.arrow_button.setExpanded(self._expanded)
        self.toggled.emit(self._expanded)
    
    def setExpanded(self, expanded):
        if self._expanded != expanded:
            self.toggle()


class FutureCodeDialog(QtWidgets.QDialog):
    """Диалог для выбора кода фьючерса"""
    
    def __init__(self, parent=None, validator=None, sorted_codes=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор кода фьючерса")
        self.setMinimumWidth(400)
        self.setModal(True)
        self.validator = validator
        self.sorted_codes = sorted_codes or []
        
        layout = QtWidgets.QVBoxLayout(self)
        
        label = QtWidgets.QLabel("Код фьючерса не задан в фильтрах.\nВведите код фьючерса для анализа:")
        layout.addWidget(label)
        
        self.code_widget = FuturesCodeComboBox(self, "", sorted_codes=self.sorted_codes)
        self.code_widget.line_edit.setPlaceholderText("Введите код фьючерса (FUSD_MM_YY)...")
        self.code_widget.line_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: #ffffff;
            }
            QLineEdit:hover {
                border-color: #4a90e2;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
                border-width: 2px;
            }
        """)
        self.code_widget.button.setStyleSheet("""
            QToolButton {
                border: 1px solid #d0d0d0;
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f5f5f5;
                color: #666666;
                font-size: 10px;
            }
            QToolButton:hover {
                background-color: #e8e8e8;
                border-color: #4a90e2;
            }
        """)
        layout.addWidget(self.code_widget)
        
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red; background-color: #FFEEEE; padding: 8px; border-radius: 4px; min-height: 0px;")
        self.error_label.setWordWrap(True)
        self.error_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.error_label.setMinimumHeight(0)
        self.error_label.setMaximumHeight(16777215)
        self.error_label.hide()
        layout.addWidget(self.error_label)
        
        layout.addSpacing(5)
        
        buttons_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.setDefault(False)
        ok_btn.setAutoDefault(False)
        ok_btn.clicked.connect(self.validate_and_accept)
        cancel_btn = QtWidgets.QPushButton("Отмена")
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        
        self.code_widget.line_edit.returnPressed.connect(self.validate_and_accept)
        self.code_widget.line_edit.textChanged.connect(self.on_code_changed)
        
        self._code = None
    
    def on_code_changed(self, text):
        """Скрывает ошибку при изменении кода"""
        if self.error_label.isVisible():
            self.error_label.setMinimumHeight(0)
            self.error_label.hide()
            self.adjustSize()
    
    def validate_and_accept(self):
        """Проверяет код и принимает диалог, если они корректны"""
        code = self.code_widget.currentText().strip()
        
        if not code:
            self.show_error("Код фьючерса не может быть пустым")
            self._code = None
            return
        
        valid, errors = FuturesValidator.validate_future_code(code)
        
        if not valid:
            error_text = "\n".join(errors) if errors else "Код фьючерса неверного формата"
            self.show_error(error_text)
            self._code = None
            return
        
        if self.validator:
            valid, validator_errors = self.validator(code)
            if not valid:
                error_text = "\n".join(validator_errors) if validator_errors else "Код фьючерса не найден в базе данных"
                self.show_error(error_text)
                self._code = None
                return
        
        self._code = code
        self.accept()
    
    def show_error(self, error_message: str):
        """Отображает сообщение об ошибке в диалоге и адаптирует размер диалога"""
        if not error_message:
            self.error_label.hide()
            self.error_label.setMinimumHeight(0)
            self.adjustSize()
            return
        
        formatted_message = error_message
        if "\n" in error_message:
            lines = error_message.split("\n")
            if len(lines) > 1:
                formatted_message = "• " + "\n• ".join(line for line in lines if line.strip())
        
        self.error_label.setText(formatted_message)
        self.error_label.setMinimumHeight(50)
        self.error_label.setMaximumHeight(16777215)
        self.error_label.setVisible(True)
        self.error_label.show()
        self.error_label.raise_()
        
        self.error_label.adjustSize()
        self.layout().update()
        self.adjustSize()
        self.update()
        
        self.code_widget.line_edit.setFocus()
    
    def get_code(self):
        """Возвращает выбранный код"""
        return self._code
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == QtCore.Qt.Key.Key_Return or event.key() == QtCore.Qt.Key.Key_Enter:
            if self.focusWidget() == self.code_widget.line_edit:
                self.validate_and_accept()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)


class CombinedPage(QtWidgets.QWidget):
    """Совмещённая таблица с фильтрами"""
    
    # Сигнал для уведомления о выделении строки
    row_selected = QtCore.Signal(int)
    
    # Сигнал для переноса отфильтрованных данных в анализ
    transfer_filtered_to_analytics = QtCore.Signal(str, date, date, object, object, object, object)
    
    def __init__(self):
        super().__init__()
        self.model = CombinedTableModel()
        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)
        self.view.horizontalHeader().setSortIndicator(0, QtCore.Qt.AscendingOrder)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().setStretchLastSection(True)
        
        # Настройка выделения строк
        self.view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        
        # Подключаем сигнал выделения строки
        self.view.selectionModel().selectionChanged.connect(self.on_row_selected)

        # Создаем панель фильтров
        self.create_filters_panel()
        
        # Создаем основной layout
        v = QtWidgets.QVBoxLayout(self)
        v.addWidget(self.filters_panel)
        v.addWidget(self.view)
        
        # Добавляем статусную строку
        self.status_label = QtWidgets.QLabel()
        v.addWidget(self.status_label)
        
        # Инициализируем фильтры после создания UI
        self.initialize_filters()
        self.update_status()

    def create_filters_panel(self):
        """Создать панель фильтров"""
        self.filters_panel = QtWidgets.QGroupBox()
        self.filters_panel.setStyleSheet("""
            QGroupBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #fafafa;
            }
        """)
        
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(12, 0, 12, 8)
        header_layout.setSpacing(0)
        
        self.header = CollapsibleHeader("Фильтры")
        self.header.toggled.connect(self.on_filters_toggled)
        self.header.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        header_layout.addWidget(self.header)
        
        panel_layout = QtWidgets.QVBoxLayout(self.filters_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        panel_layout.addLayout(header_layout)
        
        self.filters_content = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(self.filters_content)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        date_label = QtWidgets.QLabel("Период торгов:")
        date_label.setStyleSheet("font-weight: 500; color: #555555;")
        layout.addWidget(date_label, 0, 0)
        
        date_container = QtWidgets.QHBoxLayout()
        date_container.setSpacing(8)
        
        self.trade_date_from = CustomDateEdit(QtCore.QDate(1995, 1, 1), self)
        self.trade_date_from.dateChanged.connect(self.on_trade_date_from_changed)
        date_container.addWidget(self.trade_date_from)
        
        dash_label = QtWidgets.QLabel("—")
        dash_label.setAlignment(QtCore.Qt.AlignCenter)
        dash_label.setStyleSheet("color: #888888; font-weight: 500;")
        date_container.addWidget(dash_label)
        
        self.trade_date_to = CustomDateEdit(QtCore.QDate(1998, 12, 31), self)
        self.trade_date_to.dateChanged.connect(self.on_trade_date_to_changed)
        date_container.addWidget(self.trade_date_to)
        
        quick_filters_label = QtWidgets.QLabel("Быстрые фильтры:")
        quick_filters_label.setStyleSheet("color: #888888; margin-left: 16px;")
        date_container.addWidget(quick_filters_label)
        
        self.quick_filter_buttons = []
        quick_filter_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px 12px;
                color: #555555;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a90e2;
                border-color: #4a90e2;
                color: white;
            }
            QPushButton:pressed {
                background-color: #357abd;
            }
        """
        
        quick_filters = [
            ("1995", lambda: self.apply_quick_filter(1995, 1995)),
            ("1996", lambda: self.apply_quick_filter(1996, 1996)),
            ("1997", lambda: self.apply_quick_filter(1997, 1997)),
            ("1998", lambda: self.apply_quick_filter(1998, 1998)),
            ("Всё", lambda: self.apply_quick_filter(1995, 1998))
        ]
        
        for label, handler in quick_filters:
            btn = QtWidgets.QPushButton(label)
            btn.setStyleSheet(quick_filter_style)
            btn.clicked.connect(handler)
            btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            date_container.addWidget(btn)
            self.quick_filter_buttons.append(btn)
        
        date_container.addStretch()
        
        layout.addLayout(date_container, 0, 1, 1, 3)
        
        separator1 = QtWidgets.QFrame()
        separator1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator1.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator1.setStyleSheet("color: #e0e0e0; max-height: 1px;")
        layout.addWidget(separator1, 1, 0, 1, 4)
        
        code_label = QtWidgets.QLabel("Код фьючерса:")
        code_label.setStyleSheet("font-weight: 500; color: #555555;")
        layout.addWidget(code_label, 2, 0)
        from ui.widgets.custom_widgets import FuturesCodeComboBox
        self.future_code_filter = FuturesCodeComboBox(self, "")
        self.future_code_filter.line_edit.setPlaceholderText("Введите код или часть кода...")
        self.future_code_filter.line_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: #ffffff;
            }
            QLineEdit:hover {
                border-color: #4a90e2;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
                border-width: 2px;
            }
        """)
        self.future_code_filter.button.setStyleSheet("""
            QToolButton {
                border: 1px solid #d0d0d0;
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f5f5f5;
                color: #666666;
                font-size: 10px;
            }
            QToolButton:hover {
                background-color: #e8e8e8;
                border-color: #4a90e2;
            }
        """)
        self.future_code_filter.textChanged.connect(self.on_future_code_changed)
        layout.addWidget(self.future_code_filter, 2, 1, 1, 3)
        
        separator2 = QtWidgets.QFrame()
        separator2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator2.setStyleSheet("color: #e0e0e0; max-height: 1px;")
        layout.addWidget(separator2, 3, 0, 1, 4)
        
        month_label = QtWidgets.QLabel("Месяц исполнения:")
        month_label.setStyleSheet("font-weight: 500; color: #555555;")
        layout.addWidget(month_label, 4, 0)
        self.expiry_month = QtWidgets.QComboBox()
        self.expiry_month.addItem("Все", None)
        for i in range(1, 13):
            self.expiry_month.addItem(f"{i:02d}", i)
        self.expiry_month.setStyleSheet("""
            QComboBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: #ffffff;
                min-width: 100px;
            }
            QComboBox:hover {
                border-color: #4a90e2;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        self.expiry_month.currentIndexChanged.connect(self.on_expiry_month_changed)
        layout.addWidget(self.expiry_month, 4, 1)
        
        year_label = QtWidgets.QLabel("Год исполнения:")
        year_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        year_label.setStyleSheet("font-weight: 500; color: #555555;")
        layout.addWidget(year_label, 4, 2)
        self.expiry_year = QtWidgets.QComboBox()
        self.expiry_year.addItem("Все", None)
        for year in range(95, 99):
            self.expiry_year.addItem(f"19{year}", year)
        self.expiry_year.setStyleSheet("""
            QComboBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: #ffffff;
                min-width: 100px;
            }
            QComboBox:hover {
                border-color: #4a90e2;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        self.expiry_year.currentIndexChanged.connect(self.on_expiry_year_changed)
        layout.addWidget(self.expiry_year, 4, 3)
        
        separator3 = QtWidgets.QFrame()
        separator3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator3.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator3.setStyleSheet("color: #e0e0e0; max-height: 1px;")
        layout.addWidget(separator3, 5, 0, 1, 4)
        
        price_label = QtWidgets.QLabel("Цена (RUB/USD):")
        price_label.setStyleSheet("font-weight: 500; color: #555555;")
        layout.addWidget(price_label, 6, 0)
        
        price_container = QtWidgets.QHBoxLayout()
        price_container.setSpacing(8)
        
        self.price_from = QtWidgets.QDoubleSpinBox()
        self.price_from.setRange(0.0, 999999.0)
        self.price_from.setDecimals(2)
        self.price_from.setValue(0.0)
        self.price_from.setSpecialValueText("")
        self.price_from.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: #ffffff;
                min-width: 120px;
            }
            QDoubleSpinBox:hover {
                border-color: #4a90e2;
            }
        """)
        self.price_from.valueChanged.connect(self.on_price_from_changed)
        price_container.addWidget(self.price_from)
        
        price_dash_label = QtWidgets.QLabel("—")
        price_dash_label.setAlignment(QtCore.Qt.AlignCenter)
        price_dash_label.setStyleSheet("color: #888888; font-weight: 500;")
        price_container.addWidget(price_dash_label)
        
        self.price_to = QtWidgets.QDoubleSpinBox()
        self.price_to.setRange(0.0, 999999.0)
        self.price_to.setDecimals(2)
        self.price_to.setValue(999999.0)
        self.price_to.setSpecialValueText("")
        self.price_to.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: #ffffff;
                min-width: 120px;
            }
            QDoubleSpinBox:hover {
                border-color: #4a90e2;
            }
        """)
        self.price_to.valueChanged.connect(self.on_price_to_changed)
        price_container.addWidget(self.price_to)
        price_container.addStretch()
        
        layout.addLayout(price_container, 6, 1, 1, 3)
        
        separator4 = QtWidgets.QFrame()
        separator4.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator4.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator4.setStyleSheet("color: #e0e0e0; max-height: 1px;")
        layout.addWidget(separator4, 7, 0, 1, 4)
        
        contracts_label = QtWidgets.QLabel("Контрактов:")
        contracts_label.setStyleSheet("font-weight: 500; color: #555555;")
        layout.addWidget(contracts_label, 8, 0)
        
        contracts_container = QtWidgets.QHBoxLayout()
        contracts_container.setSpacing(8)
        
        self.contracts_from = QtWidgets.QSpinBox()
        self.contracts_from.setRange(0, 1000000)
        self.contracts_from.setValue(0)
        self.contracts_from.setStyleSheet("""
            QSpinBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: #ffffff;
                min-width: 120px;
            }
            QSpinBox:hover {
                border-color: #4a90e2;
            }
        """)
        self.contracts_from.valueChanged.connect(self.on_contracts_from_changed)
        contracts_container.addWidget(self.contracts_from)
        
        contracts_dash_label = QtWidgets.QLabel("—")
        contracts_dash_label.setAlignment(QtCore.Qt.AlignCenter)
        contracts_dash_label.setStyleSheet("color: #888888; font-weight: 500;")
        contracts_container.addWidget(contracts_dash_label)
        
        self.contracts_to = QtWidgets.QSpinBox()
        self.contracts_to.setRange(0, 1000000)
        self.contracts_to.setValue(1000000)
        self.contracts_to.setStyleSheet("""
            QSpinBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 8px;
                background-color: #ffffff;
                min-width: 120px;
            }
            QSpinBox:hover {
                border-color: #4a90e2;
            }
        """)
        self.contracts_to.valueChanged.connect(self.on_contracts_to_changed)
        contracts_container.addWidget(self.contracts_to)
        contracts_container.addStretch()
        
        layout.addLayout(contracts_container, 8, 1, 1, 3)
        
        separator5 = QtWidgets.QFrame()
        separator5.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator5.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator5.setStyleSheet("color: #e0e0e0; max-height: 1px;")
        layout.addWidget(separator5, 9, 0, 1, 4)
        
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.clear_filters_btn = QtWidgets.QPushButton("Очистить фильтры")
        self.clear_filters_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 2px solid #d0d0d0;
                border-radius: 6px;
                padding: 8px 16px;
                color: #333333;
                font-weight: 500;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border-color: #4a90e2;
            }
            QPushButton:pressed {
                background-color: #e8e8e8;
                border-color: #357abd;
            }
        """)
        self.clear_filters_btn.clicked.connect(self.clear_all_filters)
        buttons_layout.addWidget(self.clear_filters_btn)
        
        self.transfer_to_analytics_btn = QtWidgets.QPushButton("Перенести в анализ")
        self.transfer_to_analytics_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                border: 2px solid #357abd;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
                font-weight: 500;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #5aa0f2;
                border-color: #4a90e2;
            }
            QPushButton:pressed {
                background-color: #357abd;
                border-color: #2a5a8d;
            }
        """)
        self.transfer_to_analytics_btn.clicked.connect(self.transfer_filtered_to_analytics_handler)
        buttons_layout.addWidget(self.transfer_to_analytics_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout, 10, 0, 1, 4)
        
        panel_layout.addWidget(self.filters_content)
        
        self.filters_content_height = None
        self.collapse_animation = QPropertyAnimation(self.filters_content, b"maximumHeight")
        self.collapse_animation.setDuration(300)
        self.collapse_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def on_filters_toggled(self, checked):
        """Обработчик переключения видимости панели фильтров"""
        if self.filters_content_height is None:
            self.filters_content.setVisible(True)
            self.filters_content.adjustSize()
            self.filters_content_height = self.filters_content.height()
        
        self.collapse_animation.finished.disconnect()
        
        if checked:
            self.filters_content.setVisible(True)
            current_height = self.filters_content.maximumHeight() if self.filters_content.maximumHeight() > 0 else 0
            self.collapse_animation.setStartValue(current_height)
            self.collapse_animation.setEndValue(self.filters_content_height)
        else:
            current_height = self.filters_content.height()
            self.collapse_animation.setStartValue(current_height)
            self.collapse_animation.setEndValue(0)
            self.collapse_animation.finished.connect(
                lambda: self.filters_content.setVisible(False)
            )
        
        self.collapse_animation.start()

    def initialize_filters(self):
        """Инициализировать фильтры значениями по умолчанию"""
        # Устанавливаем фильтры по умолчанию на основе UI
        date_from = self.trade_date_from.date()
        date_to = self.trade_date_to.date()
        if date_from.isValid():
            self.model.set_filter('trade_date_from', date_from.toPython())
        if date_to.isValid():
            self.model.set_filter('trade_date_to', date_to.toPython())

    def apply_quick_filter(self, year_from, year_to):
        """Применить быстрый фильтр по годам"""
        start_date = QtCore.QDate(year_from, 1, 1)
        end_date = QtCore.QDate(year_to, 12, 31)
        
        self.trade_date_from.setDate(start_date)
        self.trade_date_to.setDate(end_date)
    
    def on_trade_date_from_changed(self, new_date):
        """Обработчик изменения начальной даты торгов"""
        if new_date.isValid():
            self.model.set_filter('trade_date_from', new_date.toPython())
        else:
            self.model.set_filter('trade_date_from', None)
        self.update_status()

    def on_trade_date_to_changed(self, new_date):
        """Обработчик изменения конечной даты торгов"""
        if new_date.isValid():
            self.model.set_filter('trade_date_to', new_date.toPython())
        else:
            self.model.set_filter('trade_date_to', None)
        self.update_status()

    def on_future_code_changed(self, text):
        """Обработчик изменения кода фьючерса"""
        self.model.set_filter('future_code', text)
        self.update_status()

    def on_expiry_month_changed(self, index):
        """Обработчик изменения месяца исполнения"""
        month = self.expiry_month.currentData()
        self.model.set_filter('expiry_month', month)
        self.update_status()

    def on_expiry_year_changed(self, index):
        """Обработчик изменения года исполнения"""
        year = self.expiry_year.currentData()
        self.model.set_filter('expiry_year', year)
        self.update_status()

    def on_price_from_changed(self, value):
        """Обработчик изменения минимальной цены"""
        # Если значение 0.0, не применяем фильтр
        if value == 0.0:
            self.model.set_filter('price_from', None)
        else:
            self.model.set_filter('price_from', value)
        self.update_status()

    def on_price_to_changed(self, value):
        """Обработчик изменения максимальной цены"""
        # Если значение максимальное (999999.0), не применяем фильтр
        if value >= 999999.0:
            self.model.set_filter('price_to', None)
        else:
            self.model.set_filter('price_to', value)
        self.update_status()

    def on_contracts_from_changed(self, value):
        """Обработчик изменения минимального количества контрактов"""
        # Если значение 0, не применяем фильтр
        if value == 0:
            self.model.set_filter('contracts_from', None)
        else:
            self.model.set_filter('contracts_from', value)
        self.update_status()

    def on_contracts_to_changed(self, value):
        """Обработчик изменения максимального количества контрактов"""
        # Если значение максимальное (1000000), не применяем фильтр
        if value >= 1000000:
            self.model.set_filter('contracts_to', None)
        else:
            self.model.set_filter('contracts_to', value)
        self.update_status()

    def clear_all_filters(self):
        """Очистить все фильтры"""
        self.model.clear_filters()
        
        # Сбрасываем UI элементы
        self.trade_date_from.setDate(QtCore.QDate(1995, 1, 1))
        self.trade_date_to.setDate(QtCore.QDate(1998, 12, 31))
        self.future_code_filter.setCurrentText("")
        self.expiry_month.setCurrentIndex(0)
        self.expiry_year.setCurrentIndex(0)
        self.price_from.setValue(0.0)
        self.price_to.setValue(999999.0)
        self.contracts_from.setValue(0)
        self.contracts_to.setValue(1000000)
        
        self.update_status()

    def on_row_selected(self, selected, deselected):
        """Обрабатывает выделение строки в таблице"""
        indexes = selected.indexes()
        if indexes:
            # Отправляем сигнал с индексом выделенной строки
            self.row_selected.emit(indexes[0].row())

    def transfer_filtered_to_analytics_handler(self):
        """Обработчик переноса отфильтрованных данных в анализ"""
        date_from_qdate = self.trade_date_from.date()
        date_to_qdate = self.trade_date_to.date()
        
        if not date_from_qdate.isValid():
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Неверная дата в поле 'Период торгов' (начальная дата).\nПожалуйста, введите корректную дату в формате дд/мм/гггг."
            )
            self.trade_date_from.line_edit.setFocus()
            return
        
        if not date_to_qdate.isValid():
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Неверная дата в поле 'Период торгов' (конечная дата).\nПожалуйста, введите корректную дату в формате дд/мм/гггг."
            )
            self.trade_date_to.line_edit.setFocus()
            return
        
        if not self.model.filtered_rows:
            QtWidgets.QMessageBox.warning(
                self,
                "Нет данных",
                "Нет отфильтрованных данных для переноса в анализ.\nПожалуйста, установите фильтры."
            )
            return
        
        future_code = self.model.filters.get('future_code', '').strip()
        
        if not future_code:
            sorted_codes = self._get_sorted_future_codes()
            dialog = FutureCodeDialog(self, validator=self._validate_future_code, sorted_codes=sorted_codes)
            result = dialog.exec()
            if result != QtWidgets.QDialog.DialogCode.Accepted:
                return
            
            future_code = dialog.get_code()
            if not future_code:
                return
            
            future_code = future_code.strip()
            if not future_code:
                return
        
        trade_dates = [row[0] for row in self.model.filtered_rows if row[0]]
        
        if not trade_dates:
            QtWidgets.QMessageBox.warning(
                self,
                "Нет данных",
                "Не найдено торговых дат в отфильтрованных данных."
            )
            return
        
        date_from = min(trade_dates)
        date_to = max(trade_dates)
        
        if not self._ensure_future_code_exists(future_code):
            return
        
        contracts_from = self.model.filters.get('contracts_from')
        contracts_to = self.model.filters.get('contracts_to')
        price_from = self.model.filters.get('price_from')
        price_to = self.model.filters.get('price_to')
        
        self.transfer_filtered_to_analytics.emit(future_code, date_from, date_to, contracts_from, contracts_to, price_from, price_to)
    
    def _get_sorted_future_codes(self):
        """Получить уникальные коды фьючерсов из отфильтрованных данных с учётом текущей сортировки"""
        if not self.model.filtered_rows:
            return []
        
        sort_column = self.view.horizontalHeader().sortIndicatorSection()
        sort_order = self.view.horizontalHeader().sortIndicatorOrder()
        
        codes_dict = {}
        for row in self.model.filtered_rows:
            code = row[1]
            if code and code not in codes_dict:
                codes_dict[code] = row
        
        if sort_column == 1:
            codes = sorted(codes_dict.keys(), reverse=(sort_order == QtCore.Qt.DescendingOrder))
        else:
            codes_with_data = [(code, codes_dict[code]) for code in codes_dict.keys()]
            if sort_column == 0:
                codes_with_data.sort(key=lambda x: x[1][0], reverse=(sort_order == QtCore.Qt.DescendingOrder))
            elif sort_column == 2:
                codes_with_data.sort(key=lambda x: x[1][2], reverse=(sort_order == QtCore.Qt.DescendingOrder))
            elif sort_column == 3:
                codes_with_data.sort(key=lambda x: x[1][3] if x[1][3] is not None else 0, reverse=(sort_order == QtCore.Qt.DescendingOrder))
            elif sort_column == 4:
                codes_with_data.sort(key=lambda x: x[1][4], reverse=(sort_order == QtCore.Qt.DescendingOrder))
            else:
                codes_with_data.sort(key=lambda x: x[1][0], reverse=(sort_order == QtCore.Qt.DescendingOrder))
            
            codes = [code for code, _ in codes_with_data]
        
        return codes
    
    def _validate_future_code(self, future_code: str):
        valid, errors = FuturesValidator.validate_future_code(future_code)
        if not valid:
            return False, errors
        
        try:
            with SessionLocal() as session:
                exists, db_errors = FuturesValidator.validate_code_exists(future_code, session)
        except Exception as exc:
            return False, [f"Не удалось проверить существование кода {future_code}: {exc}"]
        
        if not exists:
            return False, db_errors if db_errors else [f"Код {future_code} не найден в базе данных."]
        
        return True, []
    
    def _ensure_future_code_exists(self, future_code: str) -> bool:
        valid, errors = self._validate_future_code(future_code)
        if not valid:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "\n".join(errors) if errors else "Код фьючерса должен быть в формате FUSD_MM_YY."
            )
            return False
        
        return True
    
    def update_status(self):
        """Обновить статусную строку"""
        filtered_count = self.model.get_filtered_count()
        total_count = self.model.get_total_count()
        
        if filtered_count == total_count:
            self.status_label.setText(f"Показано записей: {total_count}")
        else:
            self.status_label.setText(f"Показано записей: {filtered_count} из {total_count}")
