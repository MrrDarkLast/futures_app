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

from analytics import calculate_price_change, plot_price_changes, generate_report
from db import SessionLocal
from models import Trade, Future


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
        
        # Выбор даты
        self.date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        control_layout.addRow("Дата анализа:", self.date_edit)
        
        # Выбор фьючерса
        self.future_combo = QtWidgets.QComboBox()
        self.future_combo.setEditable(False)  # Отключаем редактирование для надежной работы выпадающего списка
        control_layout.addRow("Код фьючерса:", self.future_combo)
        
        # Период предыстории
        self.history_spin = QtWidgets.QSpinBox()
        self.history_spin.setRange(10, 365)
        self.history_spin.setValue(30)
        self.history_spin.setSuffix(" дней")
        control_layout.addRow("Период предыстории:", self.history_spin)
        
        # Сортировка по коду
        self.sort_by_code_check = QtWidgets.QCheckBox("Сортировать по коду фьючерса")
        self.sort_by_code_check.setChecked(True)
        control_layout.addRow("", self.sort_by_code_check)
        
        # Кнопки
        buttons_layout = QtWidgets.QHBoxLayout()
        self.analyze_btn = QtWidgets.QPushButton("Анализировать")
        self.export_btn = QtWidgets.QPushButton("Экспорт отчета")
        buttons_layout.addWidget(self.analyze_btn)
        buttons_layout.addWidget(self.export_btn)
        control_layout.addRow("", buttons_layout)
        
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
    
    
        # Вкладка с отчетом
        self.report_tab = QtWidgets.QWidget()
        report_layout = QtWidgets.QVBoxLayout(self.report_tab)
        self.report_text = QtWidgets.QTextEdit()
        self.report_text.setReadOnly(True)
        report_layout.addWidget(self.report_text)
        
        # Добавляем вкладки
        self.tabs.addTab(self.chart_tab, "График")
        self.tabs.addTab(self.stats_tab, "Статистика")
        self.tabs.addTab(self.report_tab, "Отчет")
        
        # Добавляем вкладки в основной layout
        main_layout.addWidget(self.tabs)
        
        # Подключаем сигналы
        self.analyze_btn.clicked.connect(self.analyze_data)
        self.export_btn.clicked.connect(self.export_report)
        self.date_edit.dateChanged.connect(self.update_futures_list)
        self.sort_by_code_check.stateChanged.connect(self.update_futures_list)
        
        # Инициализируем список фьючерсов
        self.update_futures_list()
    
    def update_futures_list(self):
        """Обновить список фьючерсов, доступных для выбранной даты"""
        selected_date = self.date_edit.date().toPython()
        
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
                
                # Выводим отладочную информацию
                print(f"Found {len(futures)} futures with trading data")
                if futures:
                    print(f"Sample futures: {futures[:5]}")
                
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
            print(f"Ошибка при обновлении списка фьючерсов: {str(e)}")
    
    def set_analysis_params(self, future_code, trade_date):
        """Установить параметры для анализа"""
        # Устанавливаем код фьючерса
        index = self.future_combo.findText(future_code)
        if index >= 0:
            self.future_combo.setCurrentIndex(index)
        else:
            # Если код не найден в списке, обновляем список фьючерсов
            self.update_futures_list()
            # И пробуем снова
            index = self.future_combo.findText(future_code)
            if index >= 0:
                self.future_combo.setCurrentIndex(index)
                
        # Устанавливаем дату
        if isinstance(trade_date, date):
            self.date_edit.setDate(QtCore.QDate(trade_date))
    
    def analyze_data(self):
        """Анализировать данные и отобразить результаты"""
        future_code = self.future_combo.currentText()
        trade_date = self.date_edit.date().toPython()
        history_days = self.history_spin.value()
        
        if not future_code:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите код фьючерса")
            return
            
        # Получаем результаты анализа
        result = calculate_price_change(future_code, trade_date, history_days)
        
        if "error" in result:
            QtWidgets.QMessageBox.warning(self, "Ошибка", result["error"])
            return
            
        # Обновляем график
        self.update_chart(result)
        
        # Обновляем таблицу статистики
        self.update_stats_table(result)
        
        # Обновляем отчет
        self.update_report(future_code, trade_date, history_days)
        
        # Переключаемся на вкладку с графиком
        self.tabs.setCurrentIndex(0)
    
    def update_chart(self, result):
        """Обновить график на основе результатов анализа"""
        # Очищаем график
        self.chart_canvas.axes.clear()
        
        # Получаем данные
        dates = result["data"]["dates"]
        values = result["data"]["values"]
        
        # Строим график
        self.chart_canvas.axes.plot(dates, values, 'b-', marker='o')
        self.chart_canvas.axes.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        self.chart_canvas.axes.set_title(f'Логарифм изменения цены фьючерса {result["future_code"]}')
        self.chart_canvas.axes.set_xlabel('Дата')
        self.chart_canvas.axes.set_ylabel('ln(F(t)/F(t-2))')
        self.chart_canvas.axes.grid(True)
        
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
        self.add_stats_row("Количество торговых дней", str(stats["count"]))
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
    
    def update_report(self, future_code, trade_date, history_days):
        """Обновить текстовый отчет"""
        report = generate_report(future_code, trade_date, history_days)
        self.report_text.setText(report)
    
    def export_report(self):
        """Экспортировать отчет в текстовый файл"""
        future_code = self.future_combo.currentText()
        if not future_code:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите код фьючерса")
            return
            
        # Открываем диалог сохранения файла
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Сохранить отчет",
            f"report_{future_code}_{self.date_edit.date().toString('dd_MM_yyyy')}.txt",
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        
        if not file_path:
            return
            
        try:
            # Генерируем отчет
            trade_date = self.date_edit.date().toPython()
            history_days = self.history_spin.value()
            report = generate_report(future_code, trade_date, history_days)
            
            # Сохраняем в файл
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report)
                
            QtWidgets.QMessageBox.information(self, "Готово", f"Отчет сохранен в файл:\n{file_path}")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчет:\n{str(e)}")
