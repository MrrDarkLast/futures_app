from datetime import date
from typing import Optional, List, Tuple, Any
import os, sys

# Добавляем корневую директорию проекта в sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
if project_root not in sys.path:
    sys.path.append(project_root)

from PySide6 import QtCore
from sqlalchemy import select

from db import SessionLocal
from models import Trade, Expiration


class TradesTableModel(QtCore.QAbstractTableModel):
    """Модель для таблицы сделок"""
    HEADERS = ["Дата торгов", "Код", "Цена (RUB/USD)", "Контрактов"]

    def __init__(self):
        super().__init__()
        self.rows: List[Tuple] = []
        self.sort_column = 0  # По умолчанию сортировка по дате
        self.sort_order = QtCore.Qt.AscendingOrder  # По умолчанию по возрастанию
        self.sort_by_code = False  # Флаг сортировки по коду фьючерса
        self.refresh()

    def refresh(self):
        """Обновить данные из базы"""
        with SessionLocal() as s:
            query = s.query(Trade)
            
            # Определяем порядок сортировки в зависимости от флага
            if self.sort_by_code:
                # Сначала по коду, потом по дате
                query = query.order_by(Trade.future_code.asc(), Trade.trade_date.asc())
            else:
                # Сначала по дате, потом по коду
                query = query.order_by(Trade.trade_date.asc(), Trade.future_code.asc())
                
            q = query.all()
            self.rows = [
                (t.trade_date, t.future_code, float(t.price_rub_per_usd),
                 None if t.contracts_count is None else int(t.contracts_count))
                for t in q
            ]

        self.layoutChanged.emit()

    def rowCount(self, parent=None):  # type: ignore[override]
        return len(self.rows)

    def columnCount(self, parent=None):  # type: ignore[override]
        return len(self.HEADERS)

    def headerData(self, section, orientation, role):  # type: ignore[override]
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self.HEADERS[section]
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        return super().headerData(section, orientation, role)

    def data(self, index, role):  # type: ignore[override]
        if not index.isValid():
            return None
        r = self.rows[index.row()]
        c = index.column()
        if role == QtCore.Qt.DisplayRole:
            if c == 0: return r[0].strftime("%d-%m-%Y")
            if c == 1: return r[1]
            if c == 2: return f"{r[2]:.6f}"
            if c == 3: return "" if r[3] is None else str(r[3])
        elif role == QtCore.Qt.UserRole:  # Для сортировки используем исходные данные
            return r[c]
        return None

    def payload(self, row: int) -> Tuple:
        """Получить данные строки"""
        return self.rows[row]

    def append_row(self, trade_date, future_code, price, cnt):
        """Добавить строку в модель с учетом текущей сортировки."""
        new_row = (
            trade_date,
            future_code,
            float(price),
            None if cnt is None else int(cnt),
        )
        
        # Если сортировка не включена, просто добавляем в конец
        if self.sort_column is None:
            self.beginInsertRows(QtCore.QModelIndex(), len(self.rows), len(self.rows))
            self.rows.append(new_row)
            self.endInsertRows()
            return len(self.rows) - 1  # Возвращаем индекс добавленной строки
            
        # Находим позицию для вставки с учетом текущей сортировки
        insert_pos = 0
        for i, row in enumerate(self.rows):
            # Функция сравнения с учетом направления сортировки
            is_greater = False
            if self.sort_order == QtCore.Qt.AscendingOrder:
                if row[self.sort_column] is None:
                    is_greater = True
                elif new_row[self.sort_column] is None:
                    is_greater = False
                else:
                    is_greater = row[self.sort_column] > new_row[self.sort_column]
            else:  # DescendingOrder
                if row[self.sort_column] is None:
                    is_greater = False
                elif new_row[self.sort_column] is None:
                    is_greater = True
                else:
                    is_greater = row[self.sort_column] < new_row[self.sort_column]
                
            if is_greater:
                insert_pos = i
                break
            else:
                insert_pos = i + 1
                
        # Вставляем строку в нужную позицию
        self.beginInsertRows(QtCore.QModelIndex(), insert_pos, insert_pos)
        self.rows.insert(insert_pos, new_row)
        self.endInsertRows()
        
        return insert_pos  # Возвращаем индекс добавленной строки
        
    def sort(self, column, order):
        """Сортировка данных по указанному столбцу"""
        self.sort_column = column
        self.sort_order = order
        
        # Сохраняем текущую сортировку
        self.layoutAboutToBeChanged.emit()
        
        # Сортируем данные
        self.rows.sort(key=lambda x: x[column] if x[column] is not None else "", 
                      reverse=(order == QtCore.Qt.DescendingOrder))
        
        # Уведомляем о завершении сортировки
        self.layoutChanged.emit()


class ExpirationsTableModel(QtCore.QAbstractTableModel):
    """Модель для таблицы дат исполнения"""
    HEADERS = ["Код", "Дата исполнения"]

    def __init__(self):
        super().__init__()
        self.rows: List[Tuple[str, date]] = []
        self.sort_column = 0  # По умолчанию сортировка по коду
        self.sort_order = QtCore.Qt.AscendingOrder  # По умолчанию по возрастанию
        self.sort_by_code = True  # По умолчанию сортировка по коду
        self.refresh()

    def refresh(self):
        """Обновить данные из базы"""
        with SessionLocal() as s:
            query = s.query(Expiration)
            
            # Определяем порядок сортировки в зависимости от флага
            if self.sort_by_code:
                # Сортировка по коду
                query = query.order_by(Expiration.future_code.asc())
            else:
                # Сортировка по дате исполнения
                query = query.order_by(Expiration.expiry_date.asc(), Expiration.future_code.asc())
                
            q = query.all()
            self.rows = [(e.future_code, e.expiry_date) for e in q]
        self.layoutChanged.emit()

    def append_row(self, code: str, expiry: date):
        """Добавить строку в модель с учетом текущей сортировки."""
        new_row = (code, expiry)
        
        # Если сортировка не включена, просто добавляем в конец
        if self.sort_column is None:
            self.beginInsertRows(QtCore.QModelIndex(), len(self.rows), len(self.rows))
            self.rows.append(new_row)
            self.endInsertRows()
            return len(self.rows) - 1  # Возвращаем индекс добавленной строки
            
        # Находим позицию для вставки с учетом текущей сортировки
        insert_pos = 0
        for i, row in enumerate(self.rows):
            # Функция сравнения с учетом направления сортировки
            is_greater = False
            if self.sort_order == QtCore.Qt.AscendingOrder:
                if row[self.sort_column] is None:
                    is_greater = True
                elif new_row[self.sort_column] is None:
                    is_greater = False
                else:
                    is_greater = row[self.sort_column] > new_row[self.sort_column]
            else:  # DescendingOrder
                if row[self.sort_column] is None:
                    is_greater = False
                elif new_row[self.sort_column] is None:
                    is_greater = True
                else:
                    is_greater = row[self.sort_column] < new_row[self.sort_column]
                
            if is_greater:
                insert_pos = i
                break
            else:
                insert_pos = i + 1
                
        # Вставляем строку в нужную позицию
        self.beginInsertRows(QtCore.QModelIndex(), insert_pos, insert_pos)
        self.rows.insert(insert_pos, new_row)
        self.endInsertRows()
        
        return insert_pos  # Возвращаем индекс добавленной строки

    def rowCount(self, parent=None):  # type: ignore[override]
        return len(self.rows)

    def columnCount(self, parent=None):  # type: ignore[override]
        return len(self.HEADERS)

    def headerData(self, section, orientation, role):  # type: ignore[override]
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self.HEADERS[section]
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        return super().headerData(section, orientation, role)

    def data(self, index, role):  # type: ignore[override]
        if not index.isValid(): return None
        if role == QtCore.Qt.DisplayRole:
            v = self.rows[index.row()][index.column()]
            return v if isinstance(v, str) else v.strftime("%d-%m-%Y")
        elif role == QtCore.Qt.UserRole:  # Для сортировки используем исходные данные
            return self.rows[index.row()][index.column()]
        return None

    def payload(self, row: int) -> Tuple:
        """Получить данные строки"""
        return self.rows[row]
        
    def sort(self, column, order):
        """Сортировка данных по указанному столбцу"""
        self.sort_column = column
        self.sort_order = order
        
        # Сохраняем текущую сортировку
        self.layoutAboutToBeChanged.emit()
        
        # Сортируем данные
        self.rows.sort(key=lambda x: x[column] if x[column] is not None else "", 
                      reverse=(order == QtCore.Qt.DescendingOrder))
        
        # Уведомляем о завершении сортировки
        self.layoutChanged.emit()


class CombinedTableModel(QtCore.QAbstractTableModel):
    """Совмещенная модель для торгов и дат исполнения"""
    HEADERS = ["Дата торгов", "Код", "Цена", "Контрактов", "Дата исполнения"]

    def __init__(self):
        super().__init__()
        self.rows = []
        self.sort_column = 0  # По умолчанию сортировка по дате торгов
        self.sort_order = QtCore.Qt.AscendingOrder  # По умолчанию по возрастанию
        self.refresh()

    def refresh(self):
        """Обновить данные из базы"""
        with SessionLocal() as s:
            q = (
                s.query(Trade, Expiration)
                .join(Expiration, Trade.future_code == Expiration.future_code)
                .order_by(Trade.trade_date.asc(), Trade.future_code.asc())
                .all()
            )
            self.rows = [
                (
                    t.trade_date,
                    t.future_code,
                    float(t.price_rub_per_usd),
                    None if t.contracts_count is None else int(t.contracts_count),
                    e.expiry_date,
                )
                for t, e in q
            ]
        self.layoutChanged.emit()

    def rowCount(self, parent=None):  # type: ignore[override]
        return len(self.rows)

    def columnCount(self, parent=None):  # type: ignore[override]
        return len(self.HEADERS)

    def headerData(self, section, orientation, role):  # type: ignore[override]
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self.HEADERS[section]
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        return super().headerData(section, orientation, role)

    def data(self, index, role):  # type: ignore[override]
        if not index.isValid(): return None
        r = self.rows[index.row()]
        c = index.column()
        if role == QtCore.Qt.DisplayRole:
            if c == 0: return r[0].strftime("%d-%m-%Y")
            if c == 1: return r[1]
            if c == 2: return f"{r[2]:.6f}"
            if c == 3: return "" if r[3] is None else str(r[3])
            if c == 4: return r[4].strftime("%d-%m-%Y")
        elif role == QtCore.Qt.UserRole:  # Для сортировки используем исходные данные
            return r[c]
        return None
        
    def sort(self, column, order):
        """Сортировка данных по указанному столбцу"""
        self.sort_column = column
        self.sort_order = order
        
        # Сохраняем текущую сортировку
        self.layoutAboutToBeChanged.emit()
        
        # Сортируем данные
        self.rows.sort(key=lambda x: x[column] if x[column] is not None else "", 
                      reverse=(order == QtCore.Qt.DescendingOrder))
        
        # Уведомляем о завершении сортировки
        self.layoutChanged.emit()