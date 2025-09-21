from __future__ import annotations   # ← Должно быть самым первым

from datetime import date
from typing import Optional
import os
from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QAction     # ← QAction из QtGui
from sqlalchemy import select, delete

from db import SessionLocal
from models import Trade, Expiration
from services import (
    init_db,
    import_expirations_xls,
    import_trades_xls,
    delete_trades_by_date,
    ValidationError,
)


# ---------------- Table Models ----------------
class TradesTableModel(QtCore.QAbstractTableModel):
    HEADERS = ["Дата торгов", "Код", "Цена (RUB/USD)", "Контрактов"]

    def __init__(self):
        super().__init__()
        self.rows: list[tuple] = []
        self.refresh()

    def refresh(self):
        with SessionLocal() as s:
            q = (
                s.query(Trade)
                .order_by(Trade.trade_date.asc(), Trade.future_code.asc())
                .all()
            )
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

    # TradesTableModel
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
            if c == 0: return r[0].isoformat()
            if c == 1: return r[1]
            if c == 2: return f"{r[2]:.6f}"
            if c == 3: return "" if r[3] is None else str(r[3])
        return None

    def payload(self, row: int): return self.rows[row]

    def append_row(self, trade_date, future_code, price, cnt):
        """Добавить строку в конец модели без полного refresh()."""
        new_row = (
            trade_date,
            future_code,
            float(price),
            None if cnt is None else int(cnt),
        )
        self.beginInsertRows(QtCore.QModelIndex(), len(self.rows), len(self.rows))
        self.rows.append(new_row)
        self.endInsertRows()


class ExpirationsTableModel(QtCore.QAbstractTableModel):
    HEADERS = ["Код", "Дата исполнения"]

    def __init__(self):
        super().__init__()
        self.rows: list[tuple[str, date]] = []
        self.refresh()

    def refresh(self):
        with SessionLocal() as s:
            q = s.query(Expiration).order_by(Expiration.future_code.asc()).all()
            self.rows = [(e.future_code, e.expiry_date) for e in q]
        self.layoutChanged.emit()

    def append_row(self, code: str, expiry: date):
        """Локально добавить строку в конец модели (без полного refresh)."""
        self.beginInsertRows(QtCore.QModelIndex(), len(self.rows), len(self.rows))
        self.rows.append((code, expiry))
        self.endInsertRows()

    def rowCount(self, parent=None):  # type: ignore[override]
        return len(self.rows)

    def columnCount(self, parent=None):  # type: ignore[override]
        return len(self.HEADERS)

    # ExpirationsTableModel
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
            return v if isinstance(v, str) else v.isoformat()

    def payload(self, row: int): return self.rows[row]


class CombinedTableModel(QtCore.QAbstractTableModel):
    HEADERS = ["Дата торгов", "Код", "Цена", "Контрактов", "Дата исполнения"]

    def __init__(self):
        super().__init__()
        self.rows = []
        self.refresh()

    def refresh(self):
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

    # CombinedTableModel
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
            if c == 0: return r[0].isoformat()
            if c == 1: return r[1]
            if c == 2: return f"{r[2]:.6f}"
            if c == 3: return "" if r[3] is None else str(r[3])
            if c == 4: return r[4].isoformat()


# ---------------- Dialogs ----------------
class ImportDialog(QtWidgets.QDialog):
    def __init__(self, parent, title, handler, modes):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.handler = handler
        self.path = QtWidgets.QLineEdit(); self.path.setReadOnly(True)
        browse = QtWidgets.QPushButton("Выбрать файл…"); browse.clicked.connect(self.browse)
        self.mode = QtWidgets.QComboBox(); self.mode.addItems(modes)
        ok = QtWidgets.QPushButton("Импорт"); ok.clicked.connect(self.run)
        cancel = QtWidgets.QPushButton("Отмена"); cancel.clicked.connect(self.reject)
        row = QtWidgets.QHBoxLayout(); row.addWidget(self.path); row.addWidget(browse)
        form = QtWidgets.QFormLayout(); form.addRow("Файл", row); form.addRow("Режим", self.mode)
        btns = QtWidgets.QHBoxLayout(); btns.addWidget(ok); btns.addWidget(cancel)
        v = QtWidgets.QVBoxLayout(self); v.addLayout(form); v.addLayout(btns)

    def browse(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выбор Excel", filter="Excel (*.xls *.xlsx)")
        if p: self.path.setText(p)

    def run(self):
        if not self.path.text():
            QtWidgets.QMessageBox.warning(self, "Импорт", "Выбери файл."); return
        try:
            self.handler(self.path.text(), self.mode.currentText()); self.accept()
        except ValidationError as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка валидации", "\n".join(e.errors))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))


class TradeEditDialog(QtWidgets.QDialog):
    def __init__(self, parent, *, day: Optional[date]=None, code: str="", price: float=1.0,
                 contracts: Optional[int]=None, title="Запись торгов"):
        super().__init__(parent); self.setWindowTitle(title)
        self.dateEdit = QtWidgets.QDateEdit(QtCore.QDate.currentDate() if day is None else QtCore.QDate(day))
        self.dateEdit.setCalendarPopup(True)
        self.code = QtWidgets.QLineEdit(code)
        self.price = QtWidgets.QLineEdit(f"{price}")
        self.contracts = QtWidgets.QLineEdit("" if contracts is None else f"{contracts}")
        form = QtWidgets.QFormLayout()
        form.addRow("Дата", self.dateEdit)
        form.addRow("Код", self.code)
        form.addRow("Цена (RUB/USD)", self.price)
        form.addRow("Контрактов", self.contracts)
        ok = QtWidgets.QPushButton("Сохранить"); ok.clicked.connect(self.accept)
        cancel = QtWidgets.QPushButton("Отмена"); cancel.clicked.connect(self.reject)
        btns = QtWidgets.QHBoxLayout(); btns.addWidget(ok); btns.addWidget(cancel)
        v = QtWidgets.QVBoxLayout(self); v.addLayout(form); v.addLayout(btns)

    def values(self):
        d = self.dateEdit.date().toPython()
        c = self.code.text().strip()
        p = float(self.price.text())
        cnt_txt = self.contracts.text().strip()
        cnt = None if cnt_txt == "" else int(cnt_txt)
        return d, c, p, cnt


class ExpirationEditDialog(QtWidgets.QDialog):
    def __init__(self, parent, *, code: str="", expiry: Optional[date]=None, title="Дата исполнения"):
        super().__init__(parent); self.setWindowTitle(title)
        self.code = QtWidgets.QLineEdit(code)
        self.dateEdit = QtWidgets.QDateEdit(QtCore.QDate.currentDate() if expiry is None else QtCore.QDate(expiry))
        self.dateEdit.setCalendarPopup(True)
        form = QtWidgets.QFormLayout(); form.addRow("Код", self.code); form.addRow("Дата исполнения", self.dateEdit)
        ok = QtWidgets.QPushButton("Сохранить"); ok.clicked.connect(self.accept)
        cancel = QtWidgets.QPushButton("Отмена"); cancel.clicked.connect(self.reject)
        btns = QtWidgets.QHBoxLayout(); btns.addWidget(ok); btns.addWidget(cancel)
        v = QtWidgets.QVBoxLayout(self); v.addLayout(form); v.addLayout(btns)

    def values(self):
        return self.code.text().strip(), self.dateEdit.date().toPython()


# ---------------- Pages (Три вкладки внутри «Таблица») ----------------
class TradesPage(QtWidgets.QWidget):
    """Первая таблица: торги. Импорт/добавить/изменить/удалить/обновить."""

    def __init__(self):
        super().__init__()
        self.model = TradesTableModel()

        toolbar = QtWidgets.QToolBar()
        a_add = QAction("Добавить", self)
        a_edit = QAction("Изменить", self)
        a_del = QAction("Удалить за дату…", self)
        a_ref = QAction("Обновить", self)
        toolbar.addActions([a_add, a_edit, a_del, a_ref])

        a_add.triggered.connect(self.add_trade)
        a_edit.triggered.connect(self.edit_trade)
        a_del.triggered.connect(self.delete_by_date)
        a_ref.triggered.connect(self.model.refresh)

        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setSortingEnabled(False)  # чтобы «конец» реально был внизу
        self.view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().setStretchLastSection(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(toolbar)
        layout.addWidget(self.view)

    def selected(self):
        idxs = self.view.selectionModel().selectedRows()
        return None if not idxs else self.model.payload(idxs[0].row())

    def add_trade(self):
        dlg = TradeEditDialog(self, title="Добавить запись")
        if not dlg.exec():
            return
        try:
            day, code, price, cnt = dlg.values()

            if not code:
                raise ValidationError(["Код не может быть пустым"])
            if price <= 0:
                raise ValidationError(["Цена должна быть > 0"])
            if cnt is not None and cnt < 0:
                raise ValidationError(["Число контрактов должно быть >= 0"])

            # Одна транзакция без вложенных begin
            from sqlalchemy import select as sa_select
            with SessionLocal.begin() as s:
                exp = s.scalars(sa_select(Expiration).where(Expiration.future_code == code)).first()
                if exp and day > exp.expiry_date:
                    raise ValidationError([f"Торги после даты исполнения: {code} @ {day}"])

                t = s.get(Trade, {"trade_date": day, "future_code": code})
                if t is None:
                    s.add(Trade(
                        trade_date=day,
                        future_code=code,
                        price_rub_per_usd=price,
                        volume_mln_rub=None,
                        contracts_count=cnt,
                    ))
                else:
                    t.price_rub_per_usd = price
                    t.contracts_count = cnt

            # локально добавим строку в конец таблицы
            self.model.append_row(day, code, price, cnt)

        except ValidationError as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка валидации", "\n".join(e.errors))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def edit_trade(self):
        sel = self.selected()
        if not sel:
            return
        day, code, price, cnt = sel
        dlg = TradeEditDialog(self, day=day, code=code, price=price, contracts=cnt, title="Изменить запись")
        if not dlg.exec():
            return
        try:
            nd, ncode, nprice, ncnt = dlg.values()
            if (nd, ncode) != (day, code):
                QtWidgets.QMessageBox.warning(self, "Предупреждение", "Ключ (дата, код) менять нельзя.")
                return
            if nprice <= 0:
                raise ValidationError(["Цена должна быть > 0"])
            if ncnt is not None and ncnt < 0:
                raise ValidationError(["Контрактов >= 0"])

            from sqlalchemy import select as sa_select
            with SessionLocal.begin() as s:
                exp = s.scalars(sa_select(Expiration).where(Expiration.future_code == code)).first()
                if exp and day > exp.expiry_date:
                    raise ValidationError([f"Торги после даты исполнения: {code} @ {day}"])

                t = s.get(Trade, {"trade_date": day, "future_code": code})
                if not t:
                    raise ValidationError([f"Не найдена запись: {code} {day}"])
                t.price_rub_per_usd = nprice
                t.contracts_count = ncnt

            # локально обновим выбранную строку
            row = self.view.selectionModel().selectedRows()[0].row()
            self.model.rows[row] = (day, code, float(nprice), None if ncnt is None else int(ncnt))
            tl = self.model.index(row, 0)
            br = self.model.index(row, self.model.columnCount() - 1)
            self.model.dataChanged.emit(tl, br)

        except ValidationError as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка валидации", "\n".join(e.errors))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def delete_by_date(self):
        dlg = QtWidgets.QDialog(self); dlg.setWindowTitle("Удаление за дату")
        d = QtWidgets.QDateEdit(QtCore.QDate.currentDate()); d.setCalendarPopup(True)
        codes = QtWidgets.QLineEdit()
        form = QtWidgets.QFormLayout(); form.addRow("Дата", d); form.addRow("Коды (через пробел, пусто=все)", codes)
        ok = QtWidgets.QPushButton("Удалить"); ok.clicked.connect(dlg.accept)
        cancel = QtWidgets.QPushButton("Отмена"); cancel.clicked.connect(dlg.reject)
        btns = QtWidgets.QHBoxLayout(); btns.addWidget(ok); btns.addWidget(cancel)
        v = QtWidgets.QVBoxLayout(dlg); v.addLayout(form); v.addLayout(btns)
        if not dlg.exec(): return
        day = d.date().toPython(); lst = [c for c in codes.text().split() if c.strip()] or None
        try:
            n = delete_trades_by_date(day, lst)
            QtWidgets.QMessageBox.information(self, "Готово", f"Удалено строк: {n}")
            self.model.refresh()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))


class ExpirationsPage(QtWidgets.QWidget):
    """Вторая таблица: даты исполнения. Импорт/добавить/изменить/удалить/обновить."""
    def __init__(self):
        super().__init__()
        self.model = ExpirationsTableModel()
        self.view = QtWidgets.QTableView(); self.view.setModel(self.model)
        self.view.setSortingEnabled(False)  # чтобы новая строка была именно внизу
        self.view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().setStretchLastSection(True)

        toolbar = QtWidgets.QToolBar()
        a_add = QAction("Добавить", self)
        a_edit = QAction("Изменить", self)
        a_del = QAction("Удалить", self)
        a_ref = QAction("Обновить", self)
        toolbar.addActions([a_add, a_edit, a_del, a_ref])

        a_add.triggered.connect(self.add_exp)
        a_edit.triggered.connect(self.edit_exp)
        a_del.triggered.connect(self.delete_exp)
        a_ref.triggered.connect(self.model.refresh)

        layout = QtWidgets.QVBoxLayout(self); layout.addWidget(toolbar); layout.addWidget(self.view)

    def selected(self):
        idxs = self.view.selectionModel().selectedRows()
        return None if not idxs else self.model.payload(idxs[0].row())

    def add_exp(self):
        d = ExpirationEditDialog(self, title="Добавить дату исполнения")
        if not d.exec():
            return
        try:
            code, expiry = d.values()
            if not code:
                raise ValidationError(["Код не может быть пустым"])

            from models import Future
            # одна транзакция без вложенных begin()
            with SessionLocal.begin() as s:
                # гарантируем наличие futures
                if not s.get(Future, code):
                    s.add(Future(code=code))

                existing = s.get(Expiration, code)
                if existing is None:
                    s.add(Expiration(future_code=code, expiry_date=expiry))
                    # --- показать НОВУЮ строку в самом низу без refresh ---
                    self.model.append_row(code, expiry)
                else:
                    # если код уже есть — просто обновим дату и перерисуем выбранную строку
                    existing.expiry_date = expiry
                    row = self.view.selectionModel().selectedRows()
                    if row:
                        r = row[0].row()
                        self.model.rows[r] = (code, expiry)
                        tl = self.model.index(r, 0)
                        br = self.model.index(r, self.model.columnCount() - 1)
                        self.model.dataChanged.emit(tl, br)
                    else:
                        # на всякий случай, если строка не выделена
                        self.model.refresh()

        except ValidationError as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", "\n".join(e.errors))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def edit_exp(self):
        sel = self.selected()
        if not sel: return
        code, expiry = sel
        d = ExpirationEditDialog(self, code=code, expiry=expiry, title="Изменить дату исполнения")
        if not d.exec(): return
        try:
            ncode, nexp = d.values()
            if ncode != code:
                QtWidgets.QMessageBox.warning(self, "Предупреждение", "Код менять нельзя.")
                return

            with SessionLocal.begin() as s:
                e = s.get(Expiration, code)
                if not e: raise ValidationError([f"Не найдена запись: {code}"])
                e.expiry_date = nexp

            self.model.refresh()
        except ValidationError as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", "\n".join(e.errors))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def delete_exp(self):
        sel = self.selected()
        if not sel: return
        code, _ = sel
        if QtWidgets.QMessageBox.question(
                self, "Подтверждение",
                f"Удалить дату исполнения (и каскадно торги) для {code}?"
        ) != QtWidgets.QMessageBox.Yes:
            return
        try:
            from sqlalchemy import delete as sa_delete
            with SessionLocal.begin() as s:
                s.execute(sa_delete(Expiration).where(Expiration.future_code == code))
            self.model.refresh()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))


class CombinedPage(QtWidgets.QWidget):
    """Третья: совмещённая таблица (read-only) + Обновить."""
    def __init__(self):
        super().__init__()
        self.model = CombinedTableModel()
        self.view = QtWidgets.QTableView(); self.view.setModel(self.model)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().setStretchLastSection(True)

        toolbar = QtWidgets.QToolBar()
        a_ref = QAction("Обновить", self)
        toolbar.addAction(a_ref)
        a_ref.triggered.connect(self.model.refresh)

        v = QtWidgets.QVBoxLayout(self)
        v.addWidget(toolbar); v.addWidget(self.view)


# ---------------- Main Window ----------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Futures DB (Таблицы/Анализ/Отчёт/Помощь)")
        self.resize(1100, 640)

        main_tabs = QtWidgets.QTabWidget()

        # --- Раздел «Таблица» с тремя внутренними вкладками
        table_tabs = QtWidgets.QTabWidget()

        # сохраняем ссылки на страницы!
        self.trades_page = TradesPage()
        self.exp_page    = ExpirationsPage()
        self.comb_page   = CombinedPage()

        table_tabs.addTab(self.trades_page, "Первая таблица (торги)")
        table_tabs.addTab(self.exp_page,    "Вторая таблица (исполнения)")
        table_tabs.addTab(self.comb_page,   "Третья таблица (совмещённая)")

        main_tabs.addTab(table_tabs, "Таблица")

        # Заглушки для других разделов
        main_tabs.addTab(QtWidgets.QLabel("Раздел Анализ (готовим)"), "Анализ")
        main_tabs.addTab(QtWidgets.QLabel("Раздел Отчёт (готовим)"), "Отчёт")

        help_text = QtWidgets.QTextBrowser()
        help_text.setHtml(
            "<h2>Помощь</h2>"
            "<p>1) Импортируйте DATAISP (код, дата исполнения).<br>"
            "2) Импортируйте F_USD (торги).<br>"
            "3) Редактируйте, удаляйте, обновляйте из соответствующих вкладок.</p>"
        )
        main_tabs.addTab(help_text, "Помощь")

        self.setCentralWidget(main_tabs)

        # Эти refresh не обязательны, т.к. модели делают refresh() в своих __init__,
        # но если хочешь — оставь:
        for page in (self.trades_page, self.exp_page, self.comb_page):
            page.model.refresh()



def main():
    init_db()
    app = QtWidgets.QApplication([])
    w = MainWindow()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
