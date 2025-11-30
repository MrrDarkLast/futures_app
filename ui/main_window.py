from PySide6 import QtWidgets, QtCore

from ui.pages.trades_page import TradesPage
from ui.pages.expirations_page import ExpirationsPage
from ui.pages.combined_page import CombinedPage
from ui.pages.analytics_page import AnalyticsPage
from ui.pages.help_page import HelpPage


class MainWindow(QtWidgets.QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Futures DB (Таблицы/Анализ/Помощь)")
        self.resize(1100, 640)

        self.main_tabs = QtWidgets.QTabWidget()

        # --- Раздел «Таблица» с тремя внутренними вкладками
        table_tabs = QtWidgets.QTabWidget()

        # сохраняем ссылки на страницы
        self.trades_page = TradesPage()
        self.exp_page = ExpirationsPage()
        self.comb_page = CombinedPage()

        table_tabs.addTab(self.trades_page, "Торги")
        table_tabs.addTab(self.exp_page, "Исполнения")
        table_tabs.addTab(self.comb_page, "Совмещённая")

        self.main_tabs.addTab(table_tabs, "Таблица")

        # Раздел Анализ
        self.analytics_page = AnalyticsPage()
        self.main_tabs.addTab(self.analytics_page, "Анализ")
        
        # Раздел Помощь
        self.help_page = HelpPage()
        self.main_tabs.addTab(self.help_page, "Помощь")

        self.setCentralWidget(self.main_tabs)

        # Подключаем сигналы для автообновления таблиц
        self.trades_page.data_changed.connect(self.comb_page.model.refresh)
        self.exp_page.data_changed.connect(self.comb_page.model.refresh)
        
        # Добавляем связь для обновления таблицы торгов при изменении в таблице исполнений
        self.exp_page.data_changed.connect(self.trades_page.model.refresh)
        
        # Подключаем сигналы для переноса выделенной строки в анализ
        self.trades_page.row_selected.connect(self.transfer_trade_to_analytics)
        self.exp_page.row_selected.connect(self.transfer_expiration_to_analytics)
        self.comb_page.row_selected.connect(self.transfer_combined_to_analytics)
        
        # Подключаем сигнал для переноса отфильтрованных данных в анализ
        self.comb_page.transfer_filtered_to_analytics.connect(self.transfer_filtered_to_analytics)

        # Эти refresh не обязательны, т.к. модели делают refresh() в своих __init__
        for page in (self.trades_page, self.exp_page, self.comb_page):
            page.model.refresh()
            
    def transfer_trade_to_analytics(self, row_index):
        """Передает данные из выделенной строки таблицы торгов в раздел анализа"""
        if row_index is None or row_index < 0:
            return
            
        # Получаем данные из модели
        future_code = self.trades_page.model.data(self.trades_page.model.index(row_index, 1), QtCore.Qt.DisplayRole)
        trade_date = self.trades_page.model.data(self.trades_page.model.index(row_index, 0), QtCore.Qt.UserRole)
        
        if future_code and trade_date:
            # Устанавливаем значения в форме анализа без переключения на вкладку и запуска анализа
            self.analytics_page.set_analysis_params(future_code, trade_date)
            
    def transfer_expiration_to_analytics(self, row_index):
        """Передает данные из выделенной строки таблицы исполнений в раздел анализа"""
        if row_index is None or row_index < 0:
            return
            
        # Получаем данные из модели
        future_code = self.exp_page.model.data(self.exp_page.model.index(row_index, 0), QtCore.Qt.DisplayRole)
        expiry_date = self.exp_page.model.data(self.exp_page.model.index(row_index, 1), QtCore.Qt.UserRole)
        
        if future_code:
            # Устанавливаем код фьючерса в форме анализа без переключения на вкладку и запуска анализа
            # Для даты используем текущую дату, так как дата исполнения может быть в будущем
            self.analytics_page.set_analysis_params(future_code, QtCore.QDate.currentDate().toPython())
            
    def transfer_combined_to_analytics(self, row_index):
        """Передает данные из выделенной строки совмещённой таблицы в раздел анализа"""
        if row_index is None or row_index < 0:
            return
            
        # Получаем данные напрямую из отфильтрованных строк
        # Структура: [Дата торгов, Код, Цена, Контрактов, Дата исполнения]
        if row_index < len(self.comb_page.model.filtered_rows):
            row_data = self.comb_page.model.filtered_rows[row_index]
            trade_date = row_data[0]  # Дата торгов
            future_code = row_data[1]  # Код фьючерса
            
            if future_code and trade_date:
                # Устанавливаем значения в форме анализа без переключения на вкладку и запуска анализа
                self.analytics_page.set_analysis_params(future_code, trade_date)
    
    def transfer_filtered_to_analytics(self, future_code, date_from, date_to, contracts_from, contracts_to, price_from, price_to):
        """Переносит отфильтрованные данные из совмещенной таблицы в анализ"""
        self.analytics_page.set_analysis_params_range(future_code, date_from, date_to, contracts_from, contracts_to, price_from, price_to)
        self.main_tabs.setCurrentIndex(1)
