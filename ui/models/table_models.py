from PySide6 import QtCore, QtWidgets, QtGui
from datetime import date
from db import SessionLocal
from models import Trade, Expiration


class TradesTableModel(QtCore.QAbstractTableModel):
    """Модель для таблицы сделок"""
    HEADERS = ["Дата", "Код", "Цена", "Контрактов"]

    def __init__(self):
        super().__init__()
        self.rows = []
        self.sort_by_code = False  # Флаг для сортировки по коду

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
            if c == 0:
                return r[0].strftime("%d-%m-%Y")
            if c == 1:
                return r[1]
            if c == 2:
                return f"{r[2]:.2f}"
            if c == 3:
                return "" if r[3] is None else str(r[3])
        elif role == QtCore.Qt.UserRole:
            return r[c]
        elif role == QtCore.Qt.BackgroundRole:
            contracts = r[3]
            if contracts == 0:
                return QtGui.QColor("#f5f5f5")
        elif role == QtCore.Qt.ForegroundRole:
            contracts = r[3]
            if contracts == 0:
                return QtGui.QColor("#999999")
        return None

    def payload(self, row: int):
        """Получить данные строки"""
        if 0 <= row < len(self.rows):
            return self.rows[row]
        return None

    def flags(self, index):  # type: ignore[override]
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        
        # Разрешаем редактирование всех столбцов кроме даты
        if index.column() == 0:  # Дата - только чтение
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def setData(self, index, value, role):  # type: ignore[override]
        if not index.isValid() or role != QtCore.Qt.EditRole:
            return False
        
        row = index.row()
        col = index.column()
        
        if row >= len(self.rows):
            return False
        
        try:
            # Получаем текущую строку
            trade_date, future_code, price, contracts = self.rows[row]
            
            # Обновляем соответствующее поле
            if col == 1:  # Код фьючерса
                new_code = value.strip()
                if not new_code:
                    return False
                # Обновляем в базе данных
                with SessionLocal() as s:
                    trade = s.query(Trade).filter_by(trade_date=trade_date, future_code=future_code).first()
                    if trade:
                        trade.future_code = new_code
                        s.commit()
                # Обновляем локальную копию
                self.rows[row] = (trade_date, new_code, price, contracts)
                
            elif col == 2:  # Цена
                new_price = float(value)
                if new_price <= 0:
                    return False
                # Обновляем в базе данных
                with SessionLocal() as s:
                    trade = s.query(Trade).filter_by(trade_date=trade_date, future_code=future_code).first()
                    if trade:
                        trade.price_rub_per_usd = new_price
                        s.commit()
                # Обновляем локальную копию
                self.rows[row] = (trade_date, future_code, new_price, contracts)
                
            elif col == 3:  # Количество контрактов
                if value.strip() == "":
                    new_contracts = None
                else:
                    new_contracts = int(value)
                    if new_contracts < 0:
                        return False
                # Обновляем в базе данных
                with SessionLocal() as s:
                    trade = s.query(Trade).filter_by(trade_date=trade_date, future_code=future_code).first()
                    if trade:
                        trade.contracts_count = new_contracts
                        s.commit()
                # Обновляем локальную копию
                self.rows[row] = (trade_date, future_code, price, new_contracts)
            
            # Уведомляем об изменении данных
            self.dataChanged.emit(index, index)
            return True
            
        except (ValueError, TypeError):
            return False

    def append_row(self, trade_date, future_code, price, contracts):
        """Добавить новую строку в таблицу с учетом сортировки по дате"""
        new_row = (trade_date, future_code, float(price), None if contracts is None else int(contracts))
        
        if self.sort_by_code:
            self.rows.append(new_row)
            self.rows.sort(key=lambda x: (x[1], x[0]))
        else:
            self.rows.append(new_row)
            self.rows.sort(key=lambda x: (x[0], x[1]))
        
        row_index = self.rows.index(new_row)
        self.layoutChanged.emit()
        return row_index

    def sort(self, column, order):
        """Сортировка данных по указанному столбцу"""
        self.sort_column = column
        self.sort_order = order
        
        # Обновляем флаг sort_by_code для соответствия столбцу сортировки
        self.sort_by_code = (column == 1)  # Если сортируем по столбцу "Код"
        
        # Сохраняем текущую сортировку
        self.layoutAboutToBeChanged.emit()
        
        # Сортируем данные с учетом типов данных
        def sort_key(x):
            value = x[column]
            if value is None:
                return float('-inf') if order == QtCore.Qt.AscendingOrder else float('inf')
            
            # Обработка разных типов данных для безопасного сравнения
            if isinstance(value, (int, float)):
                return (0, value)  # Числовые значения
            elif isinstance(value, str):
                return (1, value)  # Строковые значения
            elif isinstance(value, date):
                return (2, value)  # Даты
            else:
                return (3, str(value))  # Прочие типы
        
        self.rows.sort(key=sort_key, reverse=(order == QtCore.Qt.DescendingOrder))
        
        # Уведомляем о завершении сортировки
        self.layoutChanged.emit()


class ExpirationsTableModel(QtCore.QAbstractTableModel):
    """Модель для таблицы дат исполнения"""
    HEADERS = ["Код", "Дата исполнения"]

    def __init__(self):
        super().__init__()
        self.rows = []
        self.sort_column = 0  # По умолчанию сортировка по коду
        self.sort_order = QtCore.Qt.AscendingOrder  # По умолчанию по возрастанию
        self.refresh()

    def refresh(self):
        """Обновить данные из базы"""
        with SessionLocal() as s:
            q = s.query(Expiration).order_by(Expiration.future_code.asc()).all()
            self.rows = [(e.future_code, e.expiry_date) for e in q]
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
            if c == 0:
                return r[0]
            if c == 1:
                return r[1].strftime("%d-%m-%Y")
        elif role == QtCore.Qt.UserRole:  # Для сортировки используем исходные данные
            return r[c]
        return None

    def payload(self, row: int):
        """Получить данные строки"""
        if 0 <= row < len(self.rows):
            return self.rows[row]
        return None

    def append_row(self, future_code, expiry_date):
        """Добавить новую строку в конец таблицы"""
        self.rows.append((future_code, expiry_date))
        self.layoutChanged.emit()
        return len(self.rows) - 1  # Возвращаем индекс добавленной строки

    def sort(self, column, order):
        """Сортировка данных по указанному столбцу"""
        self.sort_column = column
        self.sort_order = order
        
        # Сохраняем текущую сортировку
        self.layoutAboutToBeChanged.emit()
        
        # Сортируем данные с учетом типов данных
        def sort_key(x):
            value = x[column]
            if value is None:
                return float('-inf') if order == QtCore.Qt.AscendingOrder else float('inf')
            
            # Обработка разных типов данных для безопасного сравнения
            if isinstance(value, (int, float)):
                return (0, value)  # Числовые значения
            elif isinstance(value, str):
                return (1, value)  # Строковые значения
            elif isinstance(value, date):
                return (2, value)  # Даты
            else:
                return (3, str(value))  # Прочие типы
        
        self.rows.sort(key=sort_key, reverse=(order == QtCore.Qt.DescendingOrder))
        
        # Уведомляем о завершении сортировки
        self.layoutChanged.emit()


class CombinedTableModel(QtCore.QAbstractTableModel):
    """Совмещенная модель для торгов и дат исполнения"""
    HEADERS = ["Дата торгов", "Код", "Цена", "Контрактов", "Дата исполнения"]

    def __init__(self):
        super().__init__()
        self.rows = []
        self.filtered_rows = []
        self.sort_column = 0  # По умолчанию сортировка по дате торгов
        self.sort_order = QtCore.Qt.AscendingOrder  # По умолчанию по возрастанию
        
        # Фильтры
        self.filters = {
            'trade_date_from': None,
            'trade_date_to': None,
            'future_code': '',
            'expiry_month': None,
            'expiry_year': None,
            'price_from': None,
            'price_to': None,
            'contracts_from': None,
            'contracts_to': None
        }
        
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
        self.apply_filters()
        self.layoutChanged.emit()

    def rowCount(self, parent=None):  # type: ignore[override]
        return len(self.filtered_rows)

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
        r = self.filtered_rows[index.row()]
        c = index.column()
        if role == QtCore.Qt.DisplayRole:
            if c == 0: return r[0].strftime("%d-%m-%Y")
            if c == 1: return r[1]
            if c == 2: return f"{r[2]:.6f}"
            if c == 3: return "" if r[3] is None else str(r[3])
            if c == 4: return r[4].strftime("%d-%m-%Y")
        elif role == QtCore.Qt.UserRole:
            return r[c]
        elif role == QtCore.Qt.BackgroundRole:
            contracts = r[3]
            if contracts == 0:
                return QtGui.QColor("#f5f5f5")
        elif role == QtCore.Qt.ForegroundRole:
            contracts = r[3]
            if contracts == 0:
                return QtGui.QColor("#999999")
        return None
        
    def sort(self, column, order):
        """Сортировка данных по указанному столбцу"""
        self.sort_column = column
        self.sort_order = order
        
        # Обновляем флаг sort_by_code для соответствия столбцу сортировки
        self.sort_by_code = (column == 1)  # Если сортируем по столбцу "Код"
        
        # Сохраняем текущую сортировку
        self.layoutAboutToBeChanged.emit()
        
        # Сортируем данные с учетом типов данных
        def sort_key(x):
            value = x[column]
            if value is None:
                return float('-inf') if order == QtCore.Qt.AscendingOrder else float('inf')
            
            # Обработка разных типов данных для безопасного сравнения
            if isinstance(value, (int, float)):
                return (0, value)  # Числовые значения
            elif isinstance(value, str):
                return (1, value)  # Строковые значения
            elif isinstance(value, date):
                return (2, value)  # Даты
            else:
                return (3, str(value))  # Прочие типы
        
        self.filtered_rows.sort(key=sort_key, reverse=(order == QtCore.Qt.DescendingOrder))
        
        # Уведомляем о завершении сортировки
        self.layoutChanged.emit()
    
    def apply_filters(self):
        """Применить все активные фильтры"""
        self.filtered_rows = []
        
        for row in self.rows:
            trade_date, future_code, price, contracts, expiry_date = row
            
            # Фильтр по дате торгов
            trade_date_from = self.filters['trade_date_from']
            if trade_date_from is not None and trade_date < trade_date_from:
                continue
            trade_date_to = self.filters['trade_date_to']
            if trade_date_to is not None and trade_date > trade_date_to:
                continue
            
            # Фильтр по коду фьючерса
            if self.filters['future_code'] and self.filters['future_code'].lower() not in future_code.lower():
                continue
            
            # Фильтр по месяцу исполнения
            expiry_month = self.filters['expiry_month']
            if expiry_month is not None and expiry_date.month != expiry_month:
                continue
            
            # Фильтр по году исполнения
            expiry_year = self.filters['expiry_year']
            if expiry_year is not None and expiry_date.year % 100 != expiry_year:
                continue
            
            # Фильтр по цене
            price_from = self.filters['price_from']
            if price_from is not None and price < price_from:
                continue
            price_to = self.filters['price_to']
            if price_to is not None and price > price_to:
                continue
            
            # Фильтр по количеству контрактов
            if contracts is not None:
                contracts_from = self.filters['contracts_from']
                if contracts_from is not None and contracts < contracts_from:
                    continue
                contracts_to = self.filters['contracts_to']
                if contracts_to is not None and contracts > contracts_to:
                    continue
            else:
                if self.filters['contracts_from'] is not None or self.filters['contracts_to'] is not None:
                    # Если контракты не указаны, но фильтр по контрактам активен
                    continue
            
            self.filtered_rows.append(row)
    
    def set_filter(self, filter_name, value):
        """Установить значение фильтра"""
        if filter_name in self.filters:
            self.filters[filter_name] = value
            self.apply_filters()
            self.layoutChanged.emit()
    
    def clear_filters(self):
        """Очистить все фильтры"""
        for key in self.filters:
            if key == 'future_code':
                self.filters[key] = ''
            else:
                self.filters[key] = None
        # При очистке фильтров показываем все данные
        self.filtered_rows = self.rows.copy()
        self.layoutChanged.emit()
    
    def get_filtered_count(self):
        """Получить количество отфильтрованных записей"""
        return len(self.filtered_rows)
    
    def get_total_count(self):
        """Получить общее количество записей"""
        return len(self.rows)
