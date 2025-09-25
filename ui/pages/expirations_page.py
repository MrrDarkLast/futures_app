from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QAction
from sqlalchemy import delete

from db import SessionLocal
from models import Future, Expiration, Trade
from services import ValidationError
from ui.dialogs.dialogs import ExpirationEditDialog
from ui.models.table_models import ExpirationsTableModel
from ui.pages.sort_control import SortControlWidget
from validators import FuturesValidator


class ExpirationsPage(QtWidgets.QWidget):
    """Вторая таблица: даты исполнения. Импорт/добавить/изменить/удалить/обновить."""
    
    # Сигнал для уведомления об изменениях
    data_changed = QtCore.Signal()
    
    # Сигнал для передачи выделенной строки
    row_selected = QtCore.Signal(int)
    
    def __init__(self):
        super().__init__()
        self.model = ExpirationsTableModel()
        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)  # Включаем возможность сортировки
        self.view.horizontalHeader().setSortIndicator(0, QtCore.Qt.AscendingOrder)  # По умолчанию сортировка по коду (возрастание)
        self.view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().setStretchLastSection(True)
        
        # Подключаем сигнал выделения строки
        self.view.selectionModel().selectionChanged.connect(self.on_row_selected)

        toolbar = QtWidgets.QToolBar()
        a_add = QAction("Добавить", self)
        a_edit = QAction("Изменить", self)
        a_del = QAction("Удалить", self)
        toolbar.addActions([a_add, a_edit, a_del])

        a_add.triggered.connect(self.add_exp)
        a_edit.triggered.connect(self.edit_exp)
        a_del.triggered.connect(self.delete_exp)
        
        # Устанавливаем режим сортировки по умолчанию
        self.sort_by_code = True  # По коду

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
        

    def add_exp(self):
        """Добавление новой записи даты исполнения"""
        d = ExpirationEditDialog(self, title="Добавить дату исполнения")
        
        while True:  # Цикл для возможности повторной попытки ввода
            if not d.exec():
                return  # Пользователь нажал "Отмена"
            
            try:
                code, expiry = d.values()
                is_new = True
                
                # Проверяем данные с помощью валидатора
                valid, errors = FuturesValidator.validate_expiration(code, expiry)
                if not valid:
                    d.show_error("\n".join(errors))
                    continue
                
                # Проверяем существование записи без транзакции
                with SessionLocal() as check_session:
                    # Проверяем, что код не существует в базе данных
                    e_exists = check_session.get(Expiration, code)
                    if e_exists:
                        d.show_error(f"Запись с кодом {code} уже существует")
                        continue
                
                # Отдельная транзакция для сохранения
                with SessionLocal.begin() as s:
                    if is_new:
                        s.add(Expiration(future_code=code, expiry_date=expiry))
                        # --- Показать НОВУЮ строку с учетом сортировки ---
                        row_index = self.model.append_row(code, expiry)
                        
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
                    else:
                        # Если код уже есть — просто обновим дату и перерисуем выбранную строку
                        existing = s.get(Expiration, code)
                        existing.expiry_date = expiry
                        row = self.view.selectionModel().selectedRows()
                        if row:
                            r = row[0].row()
                            self.model.rows[r] = (code, expiry)
                            tl = self.model.index(r, 0)
                            br = self.model.index(r, self.model.columnCount() - 1)
                            self.model.dataChanged.emit(tl, br)
                        else:
                            # На всякий случай, если строка не выделена
                            self.model.refresh()
                    
                    # Уведомляем об изменении данных
                    self.data_changed.emit()
                    
                    # Если дошли до этой точки без исключений, выходим из цикла
                    break
    
            except Exception as e:
                # Для неожиданных ошибок показываем сообщение в диалоге
                d.show_error(f"Неожиданная ошибка: {str(e)}")
                # Не выходим из цикла, чтобы пользователь мог исправить данные

    def edit_exp(self):
        """Редактирование существующей даты исполнения"""
        sel = self.selected()
        if not sel:
            return
        code, expiry = sel
        d = ExpirationEditDialog(self, code=code, expiry=expiry, title="Изменить дату исполнения")
        
        while True:  # Цикл для возможности повторной попытки ввода
            if not d.exec():
                return  # Пользователь нажал "Отмена"
                
            try:
                ncode, nexp = d.values()
                
                # Проверяем, что не изменен код
                if ncode != code:
                    d.show_error("Код менять нельзя.")
                    continue
                
                # Проверяем данные с помощью валидатора
                valid, errors = FuturesValidator.validate_expiration(ncode, nexp)
                if not valid:
                    d.show_error("\n".join(errors))
                    continue
                    
                # Проверяем существование записи без транзакции
                with SessionLocal() as check_session:
                    e_exists = check_session.get(Expiration, code)
                    if not e_exists:
                        d.show_error(f"Не найдена запись: {code}")
                        continue
                
                # Сохраняем изменения в базу данных
                with SessionLocal.begin() as s:
                    e = s.get(Expiration, code)
                    e.expiry_date = nexp
    
                # Обновляем модель и прокручиваем к измененной строке
                self.model.refresh()
                
                # Находим строку с обновленным кодом
                for i, row_data in enumerate(self.model.rows):
                    if row_data[0] == code:
                        # Создаем индекс для обновленной строки
                        updated_row_index = self.model.index(i, 0)
                        
                        # Прокручиваем к найденной строке
                        self.view.scrollTo(updated_row_index, QtWidgets.QAbstractItemView.PositionAtCenter)
                        
                        # Выделяем обновленную строку
                        selection = QtCore.QItemSelection(
                            updated_row_index, 
                            self.model.index(i, self.model.columnCount() - 1)
                        )
                        self.view.selectionModel().select(selection, QtCore.QItemSelectionModel.ClearAndSelect)
                        
                        # Устанавливаем фокус на обновленную строку
                        self.view.setCurrentIndex(updated_row_index)
                        self.view.setFocus()
                        break
                
                # Уведомляем об изменении данных
                self.data_changed.emit()
                
                # Если дошли до этой точки без исключений, выходим из цикла
                break
                
            except Exception as e:
                # Для неожиданных ошибок показываем сообщение в диалоге
                d.show_error(f"Неожиданная ошибка: {str(e)}")
                # Не выходим из цикла, чтобы пользователь мог исправить данные

    def delete_exp(self):
        """Удаление записи даты исполнения"""
        sel = self.selected()
        if not sel:
            return
        code, expiry = sel
        
        # Подтверждение удаления
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Подтверждение удаления")
        msg.setText(f"Удалить запись {code} ({expiry.strftime('%d-%m-%Y')})?")
        msg.setIcon(QtWidgets.QMessageBox.Question)
        
        # Меняем порядок кнопок и делаем "Нет" кнопкой по умолчанию
        no_btn = msg.addButton("Нет", QtWidgets.QMessageBox.NoRole)
        yes_btn = msg.addButton("Да", QtWidgets.QMessageBox.YesRole)
        msg.setDefaultButton(no_btn)
        
        msg.exec()
        if msg.clickedButton() != yes_btn:
            return
            
        try:
            with SessionLocal.begin() as s:
                # Сначала удаляем связанные записи торгов
                s.execute(delete(Trade).where(Trade.future_code == code))
                
                # Затем удаляем запись даты исполнения
                s.execute(delete(Expiration).where(Expiration.future_code == code))
                
            # Обновляем модель
            self.model.refresh()
            
            # Уведомляем об изменении данных
            self.data_changed.emit()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))