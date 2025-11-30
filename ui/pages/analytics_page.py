from datetime import date, timedelta
import os
import sys

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Добавляем корневую директорию проекта в sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
if project_root not in sys.path:
    sys.path.append(project_root)

from analytics import calculate_price_change
from db import SessionLocal
from models import Trade, Future
from ui.widgets.custom_widgets import CustomDateEdit


class MatplotlibCanvas(FigureCanvas):
    """Класс для отображения графиков matplotlib в Qt"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        super(MatplotlibCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        FigureCanvas.setSizePolicy(self,
                                  QtWidgets.QSizePolicy.Expanding,
                                  QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class AnalyticsPage(QtWidgets.QWidget):
    """Страница для анализа логарифма изменения цены фьючерсов"""
    
    def __init__(self):
        super().__init__()
        
        # Создаем основной layout
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Панель управления
        control_panel = QtWidgets.QGroupBox("Параметры анализа")
        control_layout = QtWidgets.QFormLayout(control_panel)
        
        # Выбор периода дат
        date_layout = QtWidgets.QHBoxLayout()
        
        self.date_from_edit = CustomDateEdit(QtCore.QDate.currentDate(), self)
        date_layout.addWidget(self.date_from_edit)
        
        date_dash_label = QtWidgets.QLabel("—")
        date_dash_label.setAlignment(QtCore.Qt.AlignCenter)
        date_layout.addWidget(date_dash_label)
        
        self.date_to_edit = CustomDateEdit(QtCore.QDate.currentDate(), self)
        date_layout.addWidget(self.date_to_edit)
        
        control_layout.addRow("Период анализа:", date_layout)
        
        # Выбор фьючерса
        self.future_combo = QtWidgets.QComboBox()
        self.future_combo.setEditable(False)  # Отключаем редактирование для надежной работы выпадающего списка
        control_layout.addRow("Код фьючерса:", self.future_combo)
        
        self.include_zero_contracts_checkbox = QtWidgets.QCheckBox("Учитывать дни с контрактами = 0")
        self.include_zero_contracts_checkbox.setChecked(False)
        self.include_zero_contracts_checkbox.setToolTip("Если выключено, анализ исключает дни, где количество контрактов равно нулю.")
        control_layout.addRow("", self.include_zero_contracts_checkbox)
        
        # Период предыстории (скрытый параметр, фиксированное значение)
        # Используется фиксированное значение 365 дней для гарантии наличия данных
        self.history_days = 365
    
        
        # Кнопки
        buttons_layout = QtWidgets.QHBoxLayout()
        self.analyze_btn = QtWidgets.QPushButton("Анализировать")
        self.export_btn = QtWidgets.QPushButton("Экспорт отчета")
        buttons_layout.addWidget(self.analyze_btn)
        buttons_layout.addWidget(self.export_btn)
        control_layout.addRow("", buttons_layout)
        
        # Флаг успешного выполнения анализа
        self.analysis_completed = False
        self._contracts_from_filter = None
        self._contracts_to_filter = None
        self._price_from_filter = None
        self._price_to_filter = None
        
        # Добавляем панель управления в основной layout
        main_layout.addWidget(control_panel)
        
        # Создаем вкладки для результатов
        self.tabs = QtWidgets.QTabWidget()
        
        # Вкладка с графиком
        self.chart_tab = QtWidgets.QWidget()
        chart_layout = QtWidgets.QVBoxLayout(self.chart_tab)
        self.chart_canvas = MatplotlibCanvas(self.chart_tab, width=10, height=6)
        chart_layout.addWidget(self.chart_canvas)
        
        # Вкладка с таблицей статистики
        self.stats_tab = QtWidgets.QWidget()
        stats_layout = QtWidgets.QVBoxLayout(self.stats_tab)
        self.stats_table = QtWidgets.QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Показатель", "Значение"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        # Делаем таблицу статистики неизменяемой
        self.stats_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        stats_layout.addWidget(self.stats_table)
        
        # Добавляем вкладки
        self.tabs.addTab(self.chart_tab, "График")
        self.tabs.addTab(self.stats_tab, "Статистика")
        
        # Добавляем вкладки в основной layout
        main_layout.addWidget(self.tabs)
        
        # Подключаем сигналы
        self.analyze_btn.clicked.connect(self.analyze_data)
        self.export_btn.clicked.connect(self.export_report)
        self.date_from_edit.dateChanged.connect(self.update_futures_list)
        # Отключено: auto_generate_future_code вызывал проблемы с неправильной подстановкой кодов
        # self.date_from_edit.dateChanged.connect(self.auto_generate_future_code)
        # self.date_to_edit.dateChanged.connect(self.auto_generate_future_code)
        
        # Инициализируем список фьючерсов
        self.update_futures_list()
    
    def auto_generate_future_code(self):
        """Автоматически выбирать существующий код фьючерса на основе даты исполнения"""
        # Используем дату "от" для поиска кода
        selected_date = self.date_from_edit.date().toPython()
        
        # Генерируем код в формате FUSD_MM_YY на основе даты исполнения
        # MM - месяц исполнения, YY - год исполнения
        month = f"{selected_date.month:02d}"
        year = f"{selected_date.year % 100:02d}"
        target_code = f"FUSD_{month}_{year}"
        
        # Ищем существующий код в списке
        index = self.future_combo.findText(target_code)
        if index >= 0:
            # Если код найден, выбираем его
            self.future_combo.setCurrentIndex(index)
    
    def update_futures_list(self):
        """Обновить список фьючерсов, доступных для выбранной даты"""
        selected_date = self.date_from_edit.date().toPython()
        
        try:
            with SessionLocal() as session:
                # Получаем все фьючерсы, для которых есть данные
                # Вместо проверки только на выбранную дату, получаем все доступные фьючерсы
                from sqlalchemy import select, func
                
                # Получаем все фьючерсы, у которых есть хотя бы одна запись торгов
                query = (
                    select(Trade.future_code)
                    .group_by(Trade.future_code)
                    .having(func.count(Trade.trade_date) >= 3)  # Нужно минимум 3 торговых дня для расчета
                )
                
                # Если нужно, добавляем сортировку
                query = query.order_by(Trade.future_code)
                
                futures = session.execute(query).scalars().all()
                
                # Сохраняем текущий выбранный элемент
                current_text = self.future_combo.currentText() if self.future_combo.count() > 0 else ""
                
                # Обновляем выпадающий список
                self.future_combo.blockSignals(True)  # Блокируем сигналы, чтобы избежать рекурсивных вызовов
                self.future_combo.clear()
                
                if futures:
                    self.future_combo.addItems(futures)
                    
                    # Восстанавливаем выбранный элемент, если он все еще доступен
                    index = self.future_combo.findText(current_text)
                    if index >= 0:
                        self.future_combo.setCurrentIndex(index)
                    else:
                        # Если предыдущий элемент недоступен, выбираем первый
                        self.future_combo.setCurrentIndex(0)
                else:
                    # Если нет данных, добавляем заглушку
                    self.future_combo.addItem("Нет данных")
                
                self.future_combo.blockSignals(False)  # Разблокируем сигналы
        except Exception as e:
            pass
    
    def set_analysis_params(self, future_code, trade_date):
        """Установить параметры для анализа"""
        # Блокируем сигналы дат, чтобы auto_generate_future_code не перезаписал код
        self.date_from_edit.blockSignals(True)
        self.date_to_edit.blockSignals(True)
        
        try:
            # Сначала обновляем список фьючерсов, чтобы убедиться, что он актуален
            self.update_futures_list()
            
            # Устанавливаем диапазон дат для анализа
            if isinstance(trade_date, date):
                qdate = QtCore.QDate(trade_date)
                # Устанавливаем выбранную дату как конечную дату
                self.date_to_edit.setDate(qdate)
                
                # Находим реальный диапазон данных для этого кода фьючерса
                from db import SessionLocal
                from models import Trade
                from sqlalchemy import and_
                
                session = SessionLocal()
                try:
                    # Находим последнюю дату торгов для этого кода
                    last_trade = session.query(Trade).filter(
                        and_(
                            Trade.future_code == future_code,
                            Trade.trade_date <= trade_date
                        )
                    ).order_by(Trade.trade_date.desc()).first()
                    
                    if last_trade:
                        # Устанавливаем начальную дату на 30 дней раньше от последней торговой даты
                        from datetime import timedelta
                        start_date = last_trade.trade_date - timedelta(days=30)
                        self.date_from_edit.setDate(QtCore.QDate(start_date))
                    else:
                        # Если нет данных, используем стандартный диапазон
                        from datetime import timedelta
                        start_date = trade_date - timedelta(days=30)
                        self.date_from_edit.setDate(QtCore.QDate(start_date))
                        
                finally:
                    session.close()
            
            # Устанавливаем код фьючерса ПОСЛЕ установки дат, чтобы он не перезаписался
            index = self.future_combo.findText(future_code)
            if index >= 0:
                self.future_combo.setCurrentIndex(index)
            
        finally:
            # Разблокируем сигналы дат
            self.date_from_edit.blockSignals(False)
            self.date_to_edit.blockSignals(False)
            
            # Параметры установлены, анализ не запускается автоматически
    
    def set_analysis_params_range(self, future_code, date_from, date_to, contracts_from=None, contracts_to=None, price_from=None, price_to=None):
        """Установить параметры для анализа с диапазоном дат"""
        self.date_from_edit.blockSignals(True)
        self.date_to_edit.blockSignals(True)
        
        try:
            self.update_futures_list()
            
            self.date_from_edit.setDate(QtCore.QDate(date_from))
            self.date_to_edit.setDate(QtCore.QDate(date_to))
            
            index = self.future_combo.findText(future_code)
            if index >= 0:
                self.future_combo.setCurrentIndex(index)
            
            self._contracts_from_filter = contracts_from
            self._contracts_to_filter = contracts_to
            self._price_from_filter = price_from
            self._price_to_filter = price_to
            
        finally:
            self.date_from_edit.blockSignals(False)
            self.date_to_edit.blockSignals(False)
    
    def analyze_data(self):
        """Анализировать данные и отобразить результаты"""
        future_code = self.future_combo.currentText()
        date_from_qdate = self.date_from_edit.date()
        date_to_qdate = self.date_to_edit.date()
        
        if not future_code:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите код фьючерса")
            return
        
        if not date_from_qdate.isValid():
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Неверная дата в поле 'Период анализа' (начальная дата).\nПожалуйста, введите корректную дату в формате дд/мм/гггг."
            )
            self.date_from_edit.line_edit.setFocus()
            return
        
        if not date_to_qdate.isValid():
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Неверная дата в поле 'Период анализа' (конечная дата).\nПожалуйста, введите корректную дату в формате дд/мм/гггг."
            )
            self.date_to_edit.line_edit.setFocus()
            return
        
        date_from = date_from_qdate.toPython()
        date_to = date_to_qdate.toPython()
        history_days = self.history_days
            
        # Проверяем корректность диапазона дат
        if date_from > date_to:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Начальная дата не может быть больше конечной")
            return
            
        include_zero_contracts = self.include_zero_contracts_checkbox.isChecked()
        
        # При ручном анализе фильтр по контрактам не применяется, если он не был установлен через перенос
        # Фильтр применяется только если он был установлен через set_analysis_params_range
        
        # Получаем результаты анализа для диапазона дат
        result = self.analyze_date_range(
            future_code,
            date_from,
            date_to,
            history_days,
            include_zero_contracts
        )
        
        if "error" in result:
            QtWidgets.QMessageBox.warning(self, "Ошибка", result["error"])
            self.analysis_completed = False  # Анализ не выполнен
            return
        
        # Проверяем количество точек данных и выводим предупреждение если их мало
        data_points = len(result.get("data", {}).get("values", []))
        if data_points < 5:
            warning_msg = f"⚠️ Предупреждение: Недостаточно данных для надежного анализа\n\n"
            warning_msg += f"Найдено точек данных: {data_points}\n"
            warning_msg += f"Рекомендуется: минимум 5 точек\n\n"
            warning_msg += f"Результаты анализа могут быть ненадежными из-за малого количества данных.\n"
            warning_msg += f"Попробуйте:\n"
            warning_msg += f"• Увеличить период анализа\n"
            warning_msg += f"• Выбрать другой код фьючерса с большим количеством данных"
            
            QtWidgets.QMessageBox.warning(self, "Недостаточно данных", warning_msg)
            
        # Обновляем график
        self.update_chart(result)
        
        # Обновляем таблицу статистики
        self.update_stats_table(result)
        
        # Отмечаем, что анализ успешно выполнен
        self.analysis_completed = True
        
        # Переключаемся на вкладку с графиком
        self.tabs.setCurrentIndex(0)
    
    def update_chart(self, result):
        """Обновить график на основе результатов анализа"""
        # Очищаем график
        self.chart_canvas.axes.clear()
        
        # Получаем данные
        dates = result["data"]["dates"]
        values = result["data"]["values"]
        
        if not dates or not values:
            self.chart_canvas.axes.text(0.5, 0.5, 'Нет данных для отображения', 
                                      ha='center', va='center', transform=self.chart_canvas.axes.transAxes)
            self.chart_canvas.draw()
            return
        
        # Строим график с правильной сортировкой
        # Данные уже должны быть отсортированы в analyze_date_range
        self.chart_canvas.axes.plot(dates, values, 'b-', marker='o', markersize=4, linewidth=1)
        self.chart_canvas.axes.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        
        # Устанавливаем заголовок
        if "date_from" in result and "date_to" in result:
            title = f'Показатель изменения цены фьючерса {result["future_code"]}\n'
            title += f'Период: {result["date_from"].strftime("%d-%m-%Y")} - {result["date_to"].strftime("%d-%m-%Y")}'
        else:
            title = f'Показатель изменения цены фьючерса {result["future_code"]}'
        
        self.chart_canvas.axes.set_title(title)
        self.chart_canvas.axes.set_xlabel('Дата')
        self.chart_canvas.axes.set_ylabel('Логарифм изменения цены')
        self.chart_canvas.axes.grid(True, alpha=0.3)
        
        # Форматируем даты на оси X в формате DD-MM-YYYY
        import matplotlib.dates as mdates
        date_format = mdates.DateFormatter('%d-%m-%Y')
        self.chart_canvas.axes.xaxis.set_major_formatter(date_format)
        
        # Поворачиваем метки дат для лучшей читаемости
        for label in self.chart_canvas.axes.get_xticklabels():
            label.set_rotation(45)
            label.set_horizontalalignment('right')
            
        self.chart_canvas.fig.tight_layout()
        self.chart_canvas.draw()
    
    def update_stats_table(self, result):
        """Обновить таблицу статистики на основе результатов анализа"""
        stats = result["statistics"]
        trends = result["trends"]
        
        # Очищаем таблицу
        self.stats_table.setRowCount(0)
        
        # Добавляем строки с данными
        self.add_stats_row("Код фьючерса", result["future_code"])
        self.add_stats_row("Дата анализа", result["trade_date"].strftime("%d-%m-%Y"))
        # Добавляем информацию о периоде анализа
        if "date_from" in result and "date_to" in result:
            period_info = f"{result['date_from'].strftime('%d-%m-%Y')} - {result['date_to'].strftime('%d-%m-%Y')}"
            self.add_stats_row("Период анализа", period_info)
            
            include_zero_contracts = result.get("include_zero_contracts", True)
            from analytics import get_trading_days
            trading_days = get_trading_days(
                result["future_code"],
                result["date_from"],
                result["date_to"],
                include_zero_contracts=include_zero_contracts,
                contracts_from=result.get("contracts_from"),
                contracts_to=result.get("contracts_to"),
                price_from=result.get("price_from"),
                price_to=result.get("price_to")
            )
            trading_days_count = len(trading_days) if trading_days else 0
            self.add_stats_row("Торговых дней в периоде", str(trading_days_count))
        self.add_stats_row("Среднее значение", f"{stats['mean']:.6f}")
        self.add_stats_row("Стандартное отклонение", f"{stats['std_dev']:.6f}")
        self.add_stats_row("Медиана", f"{stats['median']:.6f}")
        self.add_stats_row("Минимальное значение", f"{stats['min']:.6f}")
        self.add_stats_row("Максимальное значение", f"{stats['max']:.6f}")
        self.add_stats_row("Тенденция среднего", trends["mean"])
        self.add_stats_row("Тенденция дисперсии", trends["variance"])
        
        if result["current_value"] is not None:
            self.add_stats_row("Текущее значение", f"{result['current_value']:.6f}")
            
        # Подгоняем ширину столбцов
        self.stats_table.resizeColumnsToContents()
    
    def add_stats_row(self, name, value):
        """Добавить строку в таблицу статистики"""
        row = self.stats_table.rowCount()
        self.stats_table.insertRow(row)
        self.stats_table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
        self.stats_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(value)))
    
    def export_report(self):
        """Экспортировать отчет в текстовый файл"""
        # Проверяем, выполнен ли анализ
        if not self.analysis_completed:
            QtWidgets.QMessageBox.warning(
                self, 
                "Анализ не выполнен", 
                "⚠️ Экспорт отчета невозможен\n\n"
                "Сначала необходимо выполнить анализ данных.\n\n"
                "Пожалуйста:\n"
                "1. Выберите код фьючерса\n"
                "2. Укажите период анализа\n"
                "3. Нажмите кнопку 'Анализировать'"
            )
            return
        
        future_code = self.future_combo.currentText()
        if not future_code:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите код фьючерса")
            return
            
        # Открываем диалог сохранения файла
        import os
        
        # Создаем папку reports в корне проекта, если её нет
        # Используем абсолютный путь для надежности
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        reports_dir = os.path.abspath(os.path.join(project_root, "reports"))
        os.makedirs(reports_dir, exist_ok=True)
        
        default_filename = f"report_{future_code}_{self.date_from_edit.date().toString('dd_MM_yyyy')}_{self.date_to_edit.date().toString('dd_MM_yyyy')}.pdf"
        default_path = os.path.abspath(os.path.join(reports_dir, default_filename))
        
        dialog = QtWidgets.QFileDialog(self, "Сохранить отчет")
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dialog.setNameFilters(["PDF файлы (*.pdf)", "Текстовые файлы (*.txt)", "Все файлы (*.*)"])
        dialog.setDefaultSuffix("pdf")
        dialog.setDirectory(reports_dir)
        dialog.selectFile(default_filename)
        dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        
        if dialog.exec() != QtWidgets.QFileDialog.Accepted:
            return
            
        file_paths = dialog.selectedFiles()
        if not file_paths:
            return
            
        file_path = file_paths[0]
        selected_filter = dialog.selectedNameFilter()
        
        try:
            # Определяем формат файла
            is_pdf = file_path.lower().endswith('.pdf') or selected_filter.startswith('PDF')
            
            # Генерируем отчет для диапазона дат
            date_from = self.date_from_edit.date().toPython()
            date_to = self.date_to_edit.date().toPython()
            history_days = self.history_days
            
            # Анализируем диапазон дат
            include_zero_contracts = self.include_zero_contracts_checkbox.isChecked()
            result = self.analyze_date_range(
                future_code,
                date_from,
                date_to,
                history_days,
                include_zero_contracts
            )
            
            if is_pdf:
                # Создаем PDF отчет
                self.create_pdf_report(file_path, future_code, date_from, date_to, history_days, result)
            else:
                # Создаем текстовый отчет
                report = f"Отчет по анализу фьючерса {future_code}\n"
                report += f"Период анализа: {date_from.strftime('%d-%m-%Y')} - {date_to.strftime('%d-%m-%Y')}\n\n"
                
                if "error" in result:
                    report += f"Ошибка: {result['error']}\n"
                else:
                    stats = result["statistics"]
                    from analytics import get_trading_days
                    trading_days = get_trading_days(
                        future_code,
                        date_from,
                        date_to,
                        include_zero_contracts=include_zero_contracts,
                        contracts_from=self._contracts_from_filter,
                        contracts_to=self._contracts_to_filter,
                        price_from=self._price_from_filter,
                        price_to=self._price_to_filter
                    )
                    trading_days_count = len(trading_days) if trading_days else 0
                    report += f"Общая статистика по периоду:\n"
                    report += f"Количество торговых дней: {trading_days_count}\n"
                    report += f"Среднее значение: {stats['mean']:.6f}\n"
                    report += f"Стандартное отклонение: {stats['std_dev']:.6f}\n"
                    report += f"Медиана: {stats['median']:.6f}\n"
                    report += f"Минимум: {stats['min']:.6f}\n"
                    report += f"Максимум: {stats['max']:.6f}\n"
                
                # Сохраняем в файл
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
            
            QtWidgets.QMessageBox.information(self, "Готово", f"Отчет сохранен в файл:\n{file_path}")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчет:\n{str(e)}")
    
    def create_pdf_report(self, file_path, future_code, date_from, date_to, history_days, result):
        """Создать PDF отчет с графиком и статистикой"""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        from datetime import datetime
        import numpy as np
        
        with PdfPages(file_path) as pdf:
            # Создаем страницу с заголовком, статистикой и графиком
            fig = plt.figure(figsize=(8.5, 11))  # A4 размер
            
            # Заголовок
            fig.suptitle(f"Отчет по анализу фьючерса {future_code}", 
                        fontsize=18, fontweight='bold', y=0.95)
            
            # Информация о периоде
            period_info = f"Период анализа: {date_from.strftime('%d-%m-%Y')} - {date_to.strftime('%d-%m-%Y')}"
            creation_date = f"Дата создания: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
            
            # Добавляем информацию в верхней части
            info_text = f"{period_info}\n{creation_date}"
            fig.text(0.5, 0.90, info_text, fontsize=11, ha='center', va='top',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.3))
            
            if "error" in result:
                # Показываем ошибку
                error_text = f"Ошибка анализа:\n{result['error']}"
                fig.text(0.5, 0.5, error_text, fontsize=12, ha='center', va='center',
                        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightcoral", alpha=0.7))
            else:
                stats = result["statistics"]
                trends = result.get("trends", {})
                
                # Получаем количество торговых дней
                from analytics import get_trading_days
                trading_days = get_trading_days(
                    future_code,
                    date_from,
                    date_to,
                    include_zero_contracts=result.get('include_zero_contracts', True),
                    contracts_from=result.get('contracts_from'),
                    contracts_to=result.get('contracts_to'),
                    price_from=result.get('price_from'),
                    price_to=result.get('price_to')
                )
                trading_days_count = len(trading_days) if trading_days else 0
                
                # Создаем подробную статистику
                stats_text = f"""СТАТИСТИЧЕСКИЕ ПОКАЗАТЕЛИ
                
  Основные характеристики:
• Количество торговых дней: {trading_days_count}
• Среднее значение: {stats['mean']:.6f}
• Медиана: {stats['median']:.6f}
• Стандартное отклонение: {stats['std_dev']:.6f}

  Диапазон значений:
• Минимальное значение: {stats['min']:.6f}
• Максимальное значение: {stats['max']:.6f}
• Размах: {stats['max'] - stats['min']:.6f}

  Дополнительные показатели:
• Коэффициент вариации: {(stats['std_dev'] / abs(stats['mean']) * 100):.2f}%
• Квартильный размах: {stats['std_dev'] * 1.35:.6f} (приблизительно)

  Тренды:
• Среднее значение: {trends.get('mean', 'стабильное')}
• Волатильность: {trends.get('variance', 'стабильная')}"""
                
                # Добавляем статистику
                fig.text(0.05, 0.75, stats_text, fontsize=10, ha='left', va='top',
                        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.7))
                
                # Создаем график (компактный)
                if result.get("data", {}).get("dates"):
                    ax = fig.add_subplot(2, 1, 2)
                    ax.set_position([0.1, 0.05, 0.8, 0.35])  # Компактный размер
                    
                    dates = result["data"]["dates"]
                    values = result["data"]["values"]
                    
                    # Строим график
                    ax.plot(dates, values, 'b-', marker='o', markersize=3, linewidth=1.5)
                    ax.axhline(y=0, color='r', linestyle='-', alpha=0.5, linewidth=1)
                    
                    # Добавляем линию тренда
                    if len(values) > 1:
                        z = np.polyfit(range(len(values)), values, 1)
                        p = np.poly1d(z)
                        ax.plot(dates, p(range(len(values))), "r--", alpha=0.8, linewidth=2, label='Тренд')
                        ax.legend(fontsize=8)
                    
                    # Заголовок графика
                    ax.set_title(f'Логарифм изменения цены фьючерса {future_code}', 
                               fontsize=12, fontweight='bold', pad=10)
                    ax.set_xlabel('Дата', fontsize=10)
                    ax.set_ylabel('Логарифм изменения цены', fontsize=10)
                    ax.grid(True, alpha=0.3)
                    
                    # Форматируем даты на оси X
                    import matplotlib.dates as mdates
                    date_format = mdates.DateFormatter('%d-%m')
                    ax.xaxis.set_major_formatter(date_format)
                    
                    # Поворачиваем метки дат
                    for label in ax.get_xticklabels():
                        label.set_rotation(45)
                        label.set_fontsize(8)
                    
                    # Уменьшаем размер шрифта для осей
                    ax.tick_params(axis='y', labelsize=8)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
    
    def analyze_date_range(
        self,
        future_code,
        date_from,
        date_to,
        history_days,
        include_zero_contracts
    ):
        """Анализ диапазона дат - выполняет анализ только для торговых дней"""
        from analytics import calculate_price_change, get_trading_days
        
        # Получаем только торговые дни в указанном диапазоне
        trading_days = get_trading_days(
            future_code,
            date_from,
            date_to,
            include_zero_contracts=include_zero_contracts,
            contracts_from=self._contracts_from_filter,
            contracts_to=self._contracts_to_filter
        )
        
        if not trading_days:
            error_msg = f"Недостаточно данных для анализа в указанном диапазоне\n"
            error_msg += f"Найдено торговых дней: 0\n"
            error_msg += f"Требуется минимум: 3 торговых дня"
            
            return {
                "future_code": future_code,
                "date_from": date_from,
                "date_to": date_to,
                "error": error_msg,
                "include_zero_contracts": include_zero_contracts,
                "contracts_from": self._contracts_from_filter,
                "contracts_to": self._contracts_to_filter,
                "price_from": self._price_from_filter,
                "price_to": self._price_to_filter
            }
        
        results = []
        for trade_date in trading_days:
            result = calculate_price_change(
                future_code,
                trade_date,
                history_days,
                include_zero_contracts=include_zero_contracts,
                contracts_from=self._contracts_from_filter,
                contracts_to=self._contracts_to_filter,
                price_from=self._price_from_filter,
                price_to=self._price_to_filter
            )
            if "error" not in result:
                results.append(result)
        
        if not results:
            # Получаем количество торговых дней в диапазоне для информативного сообщения
            from analytics import get_trading_days
            trading_days_count = 0
            try:
                trading_days = get_trading_days(
                    future_code,
                    date_from,
                    date_to,
                    include_zero_contracts=include_zero_contracts,
                    contracts_from=self._contracts_from_filter,
                    contracts_to=self._contracts_to_filter
                )
                trading_days_count = len(trading_days) if trading_days else 0
            except:
                pass
            
            error_msg = f"Недостаточно данных для анализа в указанном диапазоне\n"
            error_msg += f"Найдено торговых дней: {trading_days_count}\n"
            error_msg += f"Требуется минимум: 3 торговых дня"
            
            return {
                "future_code": future_code,
                "date_from": date_from,
                "date_to": date_to,
                "error": error_msg,
                "include_zero_contracts": include_zero_contracts,
                "contracts_from": self._contracts_from_filter,
                "contracts_to": self._contracts_to_filter,
                "price_from": self._price_from_filter,
                "price_to": self._price_to_filter
            }
        
        # Объединяем результаты, но фильтруем по диапазону дат
        all_dates = []
        all_values = []
        all_statistics = []
        
        for result in results:
            # Фильтруем данные по выбранному диапазону
            filtered_dates = []
            filtered_values = []
            
            for i, date in enumerate(result["data"]["dates"]):
                if date_from <= date <= date_to:
                    filtered_dates.append(date)
                    filtered_values.append(result["data"]["values"][i])
            
            if filtered_dates:  # Добавляем только если есть данные в диапазоне
                all_dates.extend(filtered_dates)
                all_values.extend(filtered_values)
                all_statistics.append(result["statistics"])
        
        # Сортируем данные по дате для правильного отображения графика
        if all_dates and all_values:
            # Создаем список кортежей (дата, значение) и сортируем по дате
            sorted_data = sorted(zip(all_dates, all_values))
            all_dates, all_values = zip(*sorted_data)
            all_dates = list(all_dates)
            all_values = list(all_values)
        
        # Вычисляем общую статистику
        if all_values:
            import numpy as np
            mean_value = np.mean(all_values)
            std_dev = np.std(all_values)
            median = np.median(all_values)
            min_value = np.min(all_values)
            max_value = np.max(all_values)
        else:
            mean_value = std_dev = median = min_value = max_value = 0
        
        # Вычисляем тренды (упрощенная версия)
        mean_trend = "стабильный"
        variance_trend = "стабильная"
        
        if len(all_statistics) > 1:
            # Сравниваем средние значения
            first_mean = all_statistics[0]["mean"]
            last_mean = all_statistics[-1]["mean"]
            if last_mean > first_mean * 1.1:
                mean_trend = "растет"
            elif last_mean < first_mean * 0.9:
                mean_trend = "снижается"
            
            # Сравниваем дисперсии
            first_var = all_statistics[0]["std_dev"]
            last_var = all_statistics[-1]["std_dev"]
            if last_var > first_var * 1.1:
                variance_trend = "увеличивается"
            elif last_var < first_var * 0.9:
                variance_trend = "уменьшается"

        result = {
            "future_code": future_code,
            "date_from": date_from,
            "date_to": date_to,
            "trade_date": date_to,  # Для совместимости
            "history_days": history_days,  # Период предыстории
            "current_value": all_values[-1] if all_values else None,
            "statistics": {
                "mean": mean_value,
                "std_dev": std_dev,
                "median": median,
                "min": min_value,
                "max": max_value,
                "count": len(all_values)
            },
            "trends": {
                "mean": mean_trend,
                "variance": variance_trend
            },
            "data": {
                "dates": all_dates,
                "values": all_values
            },
            "include_zero_contracts": include_zero_contracts,
            "contracts_from": self._contracts_from_filter,
            "contracts_to": self._contracts_to_filter,
            "price_from": self._price_from_filter,
            "price_to": self._price_to_filter,
            "individual_results": results
        }
        
        print(f"Результат analyze_date_range содержит trends: {'trends' in result}")
        return result
