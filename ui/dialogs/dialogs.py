from datetime import date
from typing import Optional, Tuple

from PySide6 import QtWidgets, QtCore

from ui.widgets.custom_widgets import FuturesCodeComboBox
from services import ValidationError
from validators import FuturesValidator


class ImportDialog(QtWidgets.QDialog):
    """Диалог для импорта данных из Excel файлов"""
    
    def __init__(self, parent, title, handler, modes):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.handler = handler
        self.path = QtWidgets.QLineEdit()
        self.path.setReadOnly(True)
        browse = QtWidgets.QPushButton("Выбрать файл…")
        browse.clicked.connect(self.browse)
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(modes)
        ok = QtWidgets.QPushButton("Импорт")
        ok.clicked.connect(self.run)
        cancel = QtWidgets.QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.path)
        row.addWidget(browse)
        form = QtWidgets.QFormLayout()
        form.addRow("Файл", row)
        form.addRow("Режим", self.mode)
        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(form)
        v.addLayout(btns)

    def browse(self):
        """Выбор файла Excel для импорта"""
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выбор Excel", filter="Excel (*.xls *.xlsx)"
        )
        if p:
            self.path.setText(p)

    def run(self):
        """Запуск импорта с обработкой ошибок"""
        if not self.path.text():
            QtWidgets.QMessageBox.warning(self, "Импорт", "Выбери файл.")
            return
        try:
            self.handler(self.path.text(), self.mode.currentText())
            self.accept()
        except ValidationError as e:
            QtWidgets.QMessageBox.critical(
                self, "Ошибка валидации", "\n".join(e.errors)
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))


class TradeEditDialog(QtWidgets.QDialog):
    """Диалог для редактирования записи торгов"""
    
    def __init__(
        self,
        parent,
        *,
        day: Optional[date] = None,
        code: str = "",
        price: float = 1.0,
        contracts: Optional[int] = None,
        title="Запись торгов",
        expiry_date: Optional[date] = None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.expiry_date = expiry_date
        
        # Создаем элементы формы
        self.dateEdit = QtWidgets.QDateEdit(
            QtCore.QDate.currentDate() if day is None else QtCore.QDate(day)
        )
        self.dateEdit.setCalendarPopup(True)
        self.code = FuturesCodeComboBox(self, code)
        self.price = QtWidgets.QLineEdit(f"{price}")
        self.contracts = QtWidgets.QLineEdit(
            "" if contracts is None else f"{contracts}"
        )
        
        # Добавляем элементы в форму
        form = QtWidgets.QFormLayout()
        form.addRow("Дата", self.dateEdit)
        form.addRow("Код", self.code)
        form.addRow("Цена (RUB/USD)", self.price)
        form.addRow("Контрактов", self.contracts)
        
        # Добавляем поле для сообщений об ошибках
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        
        # Кнопки
        ok = QtWidgets.QPushButton("Сохранить")
        ok.clicked.connect(self.validate_and_accept)
        cancel = QtWidgets.QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        
        # Создаем основной макет
        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(form)
        v.addWidget(self.error_label)
        v.addLayout(btns)
    
    def show_error(self, error_message: str):
        """Отображает сообщение об ошибке в диалоге"""
        self.error_label.setText(error_message)
        self.error_label.show()
    
    def validate_and_accept(self):
        """Проверяет введенные данные и принимает диалог, если они корректны"""
        try:
            # Получаем значения и конвертируем их
            day, code, price, cnt = self.get_input_values()
            
            # Проверяем данные с помощью валидатора
            valid, errors = FuturesValidator.validate_trade(
                day, code, price, cnt, self.expiry_date
            )
            
            if valid:
                self.accept()
            else:
                # Показываем ошибки в диалоге
                self.error_label.setText("\n".join(errors))
                self.error_label.show()
                
        except ValueError as e:
            # Ошибка конвертации значений
            self.error_label.setText(f"Ошибка в формате данных: {str(e)}")
            self.error_label.show()
            
        except Exception as e:
            # Любая другая ошибка
            self.error_label.setText(f"Ошибка: {str(e)}")
            self.error_label.show()
    
    def get_input_values(self) -> Tuple[date, str, float, Optional[int]]:
        """Получить и преобразовать введенные значения"""
        d = self.dateEdit.date().toPython()
        c = self.code.currentText().strip()
        
        # Преобразуем цену
        try:
            p = float(self.price.text())
        except ValueError:
            raise ValueError("Цена должна быть числом")
            
        # Преобразуем количество контрактов
        cnt_txt = self.contracts.text().strip()
        if cnt_txt == "":
            cnt = None
        else:
            try:
                cnt = int(cnt_txt)
            except ValueError:
                raise ValueError("Количество контрактов должно быть целым числом")
                
        return d, c, p, cnt
    
    def values(self) -> Tuple[date, str, float, Optional[int]]:
        """Получить введенные значения (для совместимости с существующим кодом)"""
        return self.get_input_values()


class ExpirationEditDialog(QtWidgets.QDialog):
    """Диалог для редактирования даты исполнения"""
    
    def __init__(
        self,
        parent,
        *,
        code: str = "",
        expiry: Optional[date] = None,
        title="Дата исполнения"
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.code = FuturesCodeComboBox(self, code)
        self.dateEdit = QtWidgets.QDateEdit(
            QtCore.QDate.currentDate() if expiry is None else QtCore.QDate(expiry)
        )
        self.dateEdit.setCalendarPopup(True)
        form = QtWidgets.QFormLayout()
        form.addRow("Код", self.code)
        form.addRow("Дата исполнения", self.dateEdit)
        
        # Добавляем поле для сообщений об ошибках
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        
        # Кнопки
        ok = QtWidgets.QPushButton("Сохранить")
        ok.clicked.connect(self.validate_and_accept)
        cancel = QtWidgets.QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        
        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(form)
        v.addWidget(self.error_label)
        v.addLayout(btns)
    
    def show_error(self, error_message: str):
        """Отображает сообщение об ошибке в диалоге"""
        self.error_label.setText(error_message)
        self.error_label.show()
    
    def validate_and_accept(self):
        """Проверяет введенные данные и принимает диалог, если они корректны"""
        try:
            code, expiry_date = self.get_input_values()
            
            # Проверяем данные с помощью валидатора
            valid, errors = FuturesValidator.validate_expiration(code, expiry_date)
            
            if valid:
                self.accept()
            else:
                # Показываем ошибки в диалоге
                self.show_error("\n".join(errors))
        except Exception as e:
            # Любая другая ошибка
            self.show_error(f"Ошибка: {str(e)}")
    
    def get_input_values(self) -> Tuple[str, date]:
        """Получить введенные значения"""
        return self.code.currentText().strip(), self.dateEdit.date().toPython()
    
    def values(self) -> Tuple[str, date]:
        """Получить введенные значения (для совместимости с существующим кодом)"""
        return self.get_input_values()
