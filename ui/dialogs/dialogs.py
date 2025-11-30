from datetime import date
from typing import Optional, Tuple

from PySide6 import QtWidgets, QtCore

from ui.widgets.custom_widgets import FuturesCodeComboBox, CustomDateEdit
from services import ValidationError
from validators import FuturesValidator


class ImportDialog(QtWidgets.QDialog):
    """Диалог для импорта данных из Excel файлов"""
    
    def __init__(self, parent, title, handler, modes):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.handler = handler
        
        # Разрешаем изменение размеров диалога
        self.setMinimumWidth(400)  # Минимальная ширина для удобства
        self.setSizeGripEnabled(True)  # Добавляем уголок для изменения размера
        
        # Создаем элементы формы
        self.path = QtWidgets.QLineEdit()
        self.path.setReadOnly(True)
        self.path.setPlaceholderText("Выберите Excel файл (обязательно)")
        
        browse = QtWidgets.QPushButton("Выбрать файл…")
        browse.clicked.connect(self.browse)
        
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(modes)
        
        # Стиль для обязательных полей
        required_style = "border: 1px solid #5a8eff;"
        self.path.setStyleSheet(required_style)
        
        # Кнопки
        ok = QtWidgets.QPushButton("Импорт")
        ok.clicked.connect(self.run)
        cancel = QtWidgets.QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        
        # Компоновка
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.path)
        row.addWidget(browse)
        
        form = QtWidgets.QFormLayout()
        form.addRow("Файл *", row)
        form.addRow("Режим", self.mode)
        
        # Добавляем поле для сообщений об ошибках с настройками для автоматического расширения
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red; background-color: #FFEEEE; padding: 8px; border-radius: 4px;")
        self.error_label.setWordWrap(True)
        self.error_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.error_label.setMinimumHeight(0)  # Минимальная высота 0 для скрытого состояния
        self.error_label.hide()
        
        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        
        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(form)
        v.addWidget(self.error_label)
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
            self.show_error("Выберите файл для импорта")
            return
        try:
            self.handler(self.path.text(), self.mode.currentText())
            self.accept()
        except ValidationError as e:
            self.show_error("\n".join(e.errors))
        except Exception as e:
            self.show_error(f"Ошибка: {str(e)}")


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
        
        # Разрешаем изменение размеров диалога
        self.setMinimumWidth(400)  # Минимальная ширина для удобства
        self.setSizeGripEnabled(True)  # Добавляем уголок для изменения размера
        self.expiry_date = expiry_date
        
        # Создаем элементы формы
        initial_date = QtCore.QDate.currentDate() if day is None else QtCore.QDate(day)
        self.dateEdit = CustomDateEdit(initial_date, self)
        
        self.code = FuturesCodeComboBox(self, code)
        self.code.line_edit.setPlaceholderText("Введите код фьючерса (обязательно)")
        
        self.price = QtWidgets.QLineEdit(f"{price}")
        self.price.setPlaceholderText("Введите цену (обязательно)")
        
        self.contracts = QtWidgets.QLineEdit(
            "0" if contracts is None else f"{contracts}"
        )
        self.contracts.setPlaceholderText("Введите количество контрактов (обязательно)")
        
        # Помечаем поля как обязательные только с помощью звездочки в заголовке
        # (убираем синюю обводку)
        
        # Добавляем элементы в форму
        form = QtWidgets.QFormLayout()
        form.addRow("Дата *", self.dateEdit)
        form.addRow("Код *", self.code)
        form.addRow("Цена (RUB/USD) *", self.price)
        form.addRow("Контрактов *", self.contracts)
        
        # Добавляем поле для сообщений об ошибках с настройками для автоматического расширения
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red; background-color: #FFEEEE; padding: 8px; border-radius: 4px;")
        self.error_label.setWordWrap(True)
        self.error_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.error_label.setMinimumHeight(0)  # Минимальная высота 0 для скрытого состояния
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
        """Отображает сообщение об ошибке в диалоге и адаптирует размер диалога"""
        # Форматируем сообщение об ошибке для лучшей читаемости
        formatted_message = error_message
        if "\n" in error_message:
            # Если есть несколько строк, форматируем их как список
            lines = error_message.split("\n")
            if len(lines) > 1:
                formatted_message = "• " + "\n• ".join(line for line in lines if line.strip())
        
        # Устанавливаем текст ошибки
        self.error_label.setText(formatted_message)
        self.error_label.show()
        
        # Адаптируем размер диалога, если нужно
        self.adjustSize()
        
        # Если текст многострочный, увеличиваем высоту диалога при необходимости
        if "\n" in formatted_message:
            # Вычисляем минимальную высоту для отображения всего текста ошибки
            text_height = self.error_label.heightForWidth(self.error_label.width())
            current_height = self.height()
            min_height = current_height + text_height - self.error_label.height()
            if current_height < min_height:
                self.resize(self.width(), min_height)
    
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
        
        # Проверяем, что код не пустой
        if not c:
            raise ValueError("Код фьючерса не может быть пустым")
        
        # Преобразуем цену
        price_text = self.price.text().strip()
        if not price_text:
            raise ValueError("Цена не может быть пустой")
        try:
            p = float(price_text)
            if p <= 0:
                raise ValueError("Цена должна быть больше нуля")
        except ValueError as e:
            if "could not convert string to float" in str(e):
                raise ValueError("Цена должна быть числом")
            else:
                raise
            
        # Преобразуем количество контрактов
        cnt_txt = self.contracts.text().strip()
        if cnt_txt == "":
            raise ValueError("Количество контрактов не может быть пустым")
        else:
            try:
                cnt = int(cnt_txt)
                if cnt < 0:
                    raise ValueError("Количество контрактов не может быть отрицательным")
            except ValueError as e:
                if str(e) == "invalid literal for int() with base 10: '{}'".format(cnt_txt):
                    raise ValueError("Количество контрактов должно быть целым числом")
                else:
                    raise
                
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
        
        # Разрешаем изменение размеров диалога
        self.setMinimumWidth(400)  # Минимальная ширина для удобства
        self.setSizeGripEnabled(True)  # Добавляем уголок для изменения размера
        
        # Создаем элементы формы
        # Автоматически генерируем код на основе даты исполнения, если код не передан
        auto_generate_date = None
        if not code and expiry is not None:
            auto_generate_date = QtCore.QDate(expiry)
        elif not code:
            auto_generate_date = QtCore.QDate.currentDate()
            
        self.code = FuturesCodeComboBox(self, code, auto_generate_from_date=auto_generate_date)
        self.code.line_edit.setPlaceholderText("Введите код фьючерса (обязательно)")
        
        initial_date = QtCore.QDate.currentDate() if expiry is None else QtCore.QDate(expiry)
        self.dateEdit = CustomDateEdit(initial_date, self)
        
        # Связываем изменение даты с обновлением кода
        self.dateEdit.dateChanged.connect(self.on_date_changed)
        
        # Связываем изменение кода с обновлением даты
        self.code.textChanged.connect(self.on_code_changed)
        
        # Помечаем поля как обязательные только с помощью звездочки в заголовке
        # (убираем синюю обводку)
        
        # Создаем форму
        form = QtWidgets.QFormLayout()
        form.addRow("Код *", self.code)
        form.addRow("Дата исполнения *", self.dateEdit)
        
        # Добавляем поле для сообщений об ошибках с настройками для автоматического расширения
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red; background-color: #FFEEEE; padding: 8px; border-radius: 4px;")
        self.error_label.setWordWrap(True)
        self.error_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.error_label.setMinimumHeight(0)  # Минимальная высота 0 для скрытого состояния
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
        """Отображает сообщение об ошибке в диалоге и адаптирует размер диалога"""
        # Форматируем сообщение об ошибке для лучшей читаемости
        formatted_message = error_message
        if "\n" in error_message:
            # Если есть несколько строк, форматируем их как список
            lines = error_message.split("\n")
            if len(lines) > 1:
                formatted_message = "• " + "\n• ".join(line for line in lines if line.strip())
        
        # Устанавливаем текст ошибки
        self.error_label.setText(formatted_message)
        self.error_label.show()
        
        # Адаптируем размер диалога, если нужно
        self.adjustSize()
        
        # Если текст многострочный, увеличиваем высоту диалога при необходимости
        if "\n" in formatted_message:
            # Вычисляем минимальную высоту для отображения всего текста ошибки
            text_height = self.error_label.heightForWidth(self.error_label.width())
            current_height = self.height()
            min_height = current_height + text_height - self.error_label.height()
            if current_height < min_height:
                self.resize(self.width(), min_height)
    
    def on_date_changed(self, new_date):
        """Обработчик изменения даты - обновляет код фьючерса"""
        # Обновляем код если поле кода пустое, содержит только FUSD_, или содержит автогенерированный код
        current_code = self.code.currentText().strip()
        if (not current_code or 
            current_code == "FUSD_" or 
            current_code.startswith("FUSD_") and len(current_code) <= 6 or
            self._is_auto_generated_code(current_code)):
            self.code.update_code_from_date(new_date)
    
    def _is_auto_generated_code(self, code):
        """Проверяет, является ли код автогенерированным (можно безопасно перезаписать)"""
        # Если код соответствует формату FUSD_MM_YY, считаем его автогенерированным
        import re
        pattern = r'^FUSD_\d{2}_\d{2}$'
        return bool(re.match(pattern, code))
    
    def on_code_changed(self, new_code):
        """Обработчик изменения кода - обновляет дату на основе кода"""
        # Обновляем дату только если код соответствует формату FUSD_MM_YY
        if self._is_auto_generated_code(new_code):
            new_date = self._extract_date_from_code(new_code)
            if new_date:
                # Блокируем сигнал, чтобы избежать рекурсии
                self.dateEdit.blockSignals(True)
                self.dateEdit.setDate(new_date)
                self.dateEdit.blockSignals(False)
    
    def _extract_date_from_code(self, code):
        """Извлекает дату из кода FUSD_MM_YY"""
        import re
        match = re.match(r'^FUSD_(\d{2})_(\d{2})$', code)
        if match:
            month = int(match.group(1))
            year = int(match.group(2))
            # Преобразуем двухзначный год в четырехзначный (предполагаем 20xx)
            full_year = 2000 + year if year < 50 else 1900 + year
            try:
                # Создаем дату на 1 число месяца
                from datetime import date
                return QtCore.QDate(full_year, month, 1)
            except ValueError:
                return None
        return None
    
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
        code = self.code.currentText().strip()
        if not code:
            raise ValueError("Код фьючерса не может быть пустым")
        
        expiry_date = self.dateEdit.date().toPython()
        
        return code, expiry_date
    
    def values(self) -> Tuple[str, date]:
        """Получить введенные значения (для совместимости с существующим кодом)"""
        return self.get_input_values()
