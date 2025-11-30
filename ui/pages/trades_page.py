from datetime import date

from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QAction
from sqlalchemy import select

from db import SessionLocal
from models import Trade, Expiration
from services import delete_trades_by_date, ValidationError
from ui.dialogs.dialogs import TradeEditDialog
from ui.models.table_models import TradesTableModel
from ui.widgets.custom_widgets import CustomDateEdit, show_success_toast
from validators import FuturesValidator


class TradesPage(QtWidgets.QWidget):
    """Первая таблица: торги. Импорт/добавить/изменить/удалить/обновить."""
    
    # Сигнал для уведомления об изменениях
    data_changed = QtCore.Signal()
    
    # Сигнал для передачи выделенной строки
    row_selected = QtCore.Signal(int)

    def __init__(self):
        super().__init__()
        self.model = TradesTableModel()

        toolbar = QtWidgets.QToolBar()
        a_add = QAction("Добавить", self)
        a_edit = QAction("Изменить", self)
        a_del = QAction("Удалить за дату…", self)
        toolbar.addActions([a_add, a_edit, a_del])

        a_add.triggered.connect(self.add_trade)
        a_edit.triggered.connect(self.edit_trade)
        a_del.triggered.connect(self.delete_by_date)
        
        # Устанавливаем режим сортировки по умолчанию
        self.sort_by_code = False  # По дате

        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)  # Включаем возможность сортировки
        self.view.horizontalHeader().setSortIndicator(0, QtCore.Qt.AscendingOrder)  # По умолчанию сортировка по дате (возрастание)
        self.view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().setStretchLastSection(True)
        
        # Подключаем сигнал выделения строки
        self.view.selectionModel().selectionChanged.connect(self.on_row_selected)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(toolbar)
        layout.addWidget(self.view)

    def selected(self):
        """Получить выбранную запись"""
        idxs = self.view.selectionModel().selectedRows()
        return None if not idxs else self.model.payload(idxs[0].row())
        
    def on_row_selected(self, selected, deselected):
        """Обрабатывает выделение строки в таблице"""
        indexes = selected.indexes()
        if indexes:
            # Отправляем сигнал с индексом выделенной строки
            self.row_selected.emit(indexes[0].row())
        

    def add_trade(self):
        """Добавление новой записи торгов"""
        # Получаем дату исполнения для выбранного кода (если есть)
        expiry_date = None
        
        # Создаем диалог, передавая дату исполнения
        dlg = TradeEditDialog(self, title="Добавить запись", expiry_date=expiry_date)
        
        while True:  # Цикл для возможности повторной попытки ввода
            if not dlg.exec():
                return  # Пользователь нажал "Отмена"
                
            try:
                day, code, price, cnt = dlg.values()
                
                # Сначала проверяем данные
                with SessionLocal() as check_session:
                    # Проверяем, что код существует в базе данных
                    valid, errors = FuturesValidator.validate_code_exists(code, check_session)
                    if not valid:
                        dlg.show_error("\n".join(errors))
                        continue
                    
                    # Получаем дату исполнения для выбранного кода
                    from sqlalchemy import select as sa_select
                    exp = check_session.scalars(sa_select(Expiration).where(Expiration.future_code == code)).first()
                    expiry_date = exp.expiry_date if exp else None
                    
                    # Проверяем дату торгов относительно даты исполнения
                    if expiry_date and day > expiry_date:
                        day_str = day.strftime("%d-%m-%Y")
                        expiry_str = expiry_date.strftime("%d-%m-%Y")
                        error_msg = f"Дата торгов ({day_str}) превышает дату исполнения {expiry_str} для кода {code}"
                        dlg.show_error(error_msg)
                        continue
                    
                    # Проверяем остальные данные с помощью валидатора
                    valid, errors = FuturesValidator.validate_trade(day, code, price, cnt, expiry_date)
                    if not valid:
                        dlg.show_error("\n".join(errors))
                        continue
                
                # После всех проверок, выполняем сохранение в отдельной транзакции
                with SessionLocal.begin() as save_session:
                    # Проверяем существование записи с такой же датой и кодом
                    t = save_session.get(Trade, {"trade_date": day, "future_code": code})
                    if t is None:
                        save_session.add(Trade(
                            trade_date=day,
                            future_code=code,
                            price_rub_per_usd=price,
                            contracts_count=cnt,
                        ))
                    else:
                        # Если запись уже существует, показываем ошибку и прерываем операцию
                        dlg.show_error(f"Торг с датой {FuturesValidator.format_date(day)} и кодом {code} уже существует. "
                                      f"Используйте редактирование для изменения существующей записи.")
                        continue

                # Добавляем запись в модель с учетом текущей сортировки
                row_index = self.model.append_row(day, code, price, cnt)
                
                # Создаем индекс для новой строки
                new_row_index = self.model.index(row_index, 0)
                
                # Прокручиваем к добавленной записи
                self.view.scrollTo(new_row_index, QtWidgets.QAbstractItemView.PositionAtCenter)
                
                # Выделяем добавленную строку
                selection = QtCore.QItemSelection(
                    new_row_index, 
                    self.model.index(row_index, self.model.columnCount() - 1)
                )
                self.view.selectionModel().select(selection, QtCore.QItemSelectionModel.ClearAndSelect)
                
                # Устанавливаем фокус на новую строку
                self.view.setCurrentIndex(new_row_index)
                self.view.setFocus()
                
                show_success_toast(self, f"Торг {code} от {day.strftime('%d-%m-%Y')} успешно добавлен")
                
                # Уведомляем об изменении данных
                self.data_changed.emit()
                
                # Если дошли до этой точки без исключений, выходим из цикла
                break
                
            except Exception as e:
                # Для неожиданных ошибок показываем сообщение в диалоге
                dlg.show_error(f"Неожиданная ошибка: {str(e)}")
                # Не выходим из цикла, чтобы пользователь мог исправить данные

    def edit_trade(self):
        """Редактирование существующей записи торгов"""
        sel = self.selected()
        if not sel:
            return
            
        day, code, price, cnt = sel
        
        # Получаем дату исполнения для выбранного кода
        expiry_date = None
        from sqlalchemy import select as sa_select
        with SessionLocal() as s:
            exp = s.scalars(sa_select(Expiration).where(Expiration.future_code == code)).first()
            if exp:
                expiry_date = exp.expiry_date
                
        # Создаем диалог с передачей даты исполнения
        dlg = TradeEditDialog(
            self, 
            day=day, 
            code=code, 
            price=price, 
            contracts=cnt, 
            title="Изменить запись",
            expiry_date=expiry_date
        )
        
        while True:  # Цикл для возможности повторной попытки ввода
            if not dlg.exec():
                return  # Пользователь нажал "Отмена"
                
            try:
                nd, ncode, nprice, ncnt = dlg.values()
                
                # Проверяем, что не изменены ключевые поля
                if (nd, ncode) != (day, code):
                    dlg.show_error("Ключ (дата, код) менять нельзя.")
                    continue
                    
                # Проверяем данные с помощью валидатора
                valid, errors = FuturesValidator.validate_trade(nd, ncode, nprice, ncnt, expiry_date)
                
                if not valid:
                    dlg.show_error("\n".join(errors))
                    continue
                
                # Проверяем существование записи без транзакции
                with SessionLocal() as check_session:
                    t_exists = check_session.get(Trade, {"trade_date": day, "future_code": code})
                    if not t_exists:
                        dlg.show_error(f"Не найдена запись: {code} {day}")
                        continue
                    
                # Сохраняем изменения в базу данных в отдельной транзакции
                with SessionLocal.begin() as s:
                    t = s.get(Trade, {"trade_date": day, "future_code": code})
                    t.price_rub_per_usd = nprice
                    t.contracts_count = ncnt

                # Локально обновим выбранную строку
                row = self.view.selectionModel().selectedRows()[0].row()
                self.model.rows[row] = (day, code, float(nprice), None if ncnt is None else int(ncnt))
                tl = self.model.index(row, 0)
                br = self.model.index(row, self.model.columnCount() - 1)
                self.model.dataChanged.emit(tl, br)
                
                show_success_toast(self, f"Торг {code} от {day.strftime('%d-%m-%Y')} успешно изменён")
                
                # Уведомляем об изменении данных
                self.data_changed.emit()
                
                # Если дошли до этой точки без исключений, выходим из цикла
                break

            except Exception as e:
                # Для неожиданных ошибок показываем сообщение в диалоге
                dlg.show_error(f"Неожиданная ошибка: {str(e)}")
                # Не выходим из цикла, чтобы пользователь мог исправить данные

    def delete_by_date(self):
        """Удаление записей по дате"""
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Удаление за дату")
        d = CustomDateEdit(QtCore.QDate.currentDate(), dlg)
        codes = QtWidgets.QLineEdit()
        form = QtWidgets.QFormLayout()
        form.addRow("Дата", d)
        form.addRow("Коды (через пробел, пусто=все)", codes)
        ok = QtWidgets.QPushButton("Удалить")
        ok.clicked.connect(dlg.accept)
        cancel = QtWidgets.QPushButton("Отмена")
        cancel.clicked.connect(dlg.reject)
        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        v = QtWidgets.QVBoxLayout(dlg)
        v.addLayout(form)
        v.addLayout(btns)
        
        # Если есть выделенная строка, заполняем поля диалога
        selected_row = self.selected()
        if selected_row:
            trade_date, code, _, _ = selected_row
            # Устанавливаем дату из выделенной строки
            d.setDate(trade_date)
            # Устанавливаем код из выделенной строки
            codes.setText(code)
            
        if not dlg.exec():
            return
            
        day = d.date().toPython()
        lst = [c for c in codes.text().split() if c.strip()] or None
        
        # Показываем предупреждение перед удалением
        warning_msg = QtWidgets.QMessageBox(self)
        warning_msg.setWindowTitle("Подтверждение удаления")
        
        if lst:
            codes_text = ", ".join(lst)
            warning_msg.setText(f"Удалить записи торгов за {day.strftime('%d-%m-%Y')} по кодам: {codes_text}?")
        else:
            warning_msg.setText(f"Удалить ВСЕ записи торгов за {day.strftime('%d-%m-%Y')}?")
            
        warning_msg.setInformativeText("⚠️ ВНИМАНИЕ: Записи будут удалены отовсюду!\n\n"
                                      "• Удаляются записи торгов из таблицы 'Торги'\n"
                                      "• Записи исчезнут из совмещённой таблицы\n"
                                      "• Дата исполнения (если есть) останется без изменений")
        warning_msg.setIcon(QtWidgets.QMessageBox.Warning)
        
        # Меняем порядок кнопок и делаем "Нет" кнопкой по умолчанию
        no_btn = warning_msg.addButton("Да", QtWidgets.QMessageBox.NoRole)
        yes_btn = warning_msg.addButton("Нет", QtWidgets.QMessageBox.YesRole)
        warning_msg.setDefaultButton(no_btn)
        
        warning_msg.exec()
        if warning_msg.clickedButton() != no_btn:
            return
            
        try:
            n = delete_trades_by_date(day, lst)
            
            sort_column = self.view.horizontalHeader().sortIndicatorSection()
            sort_order = self.view.horizontalHeader().sortIndicatorOrder()
            
            self.model.refresh()
            
            self.model.sort(sort_column, sort_order)
            self.view.horizontalHeader().setSortIndicator(sort_column, sort_order)
            
            show_success_toast(self, f"Удалено записей: {n}")
            
            # Уведомляем об изменении данных
            self.data_changed.emit()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))