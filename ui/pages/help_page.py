from PySide6 import QtWidgets, QtCore, QtGui

class HelpPage(QtWidgets.QWidget):
    """Страница помощи с информацией о приложении"""
    
    def __init__(self):
        super().__init__()
        
        # Создаем основной layout
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Создаем скроллируемую область для текста справки
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        
        # Создаем виджет с содержимым справки
        help_content = QtWidgets.QWidget()
        help_layout = QtWidgets.QVBoxLayout(help_content)
        help_layout.setContentsMargins(15, 15, 15, 15)
        help_layout.setSpacing(0)
        
        # Добавляем заголовок в скроллируемую область
        title_container = QtWidgets.QWidget()
        title_container.setStyleSheet("""
            QWidget {
                background-color: #3498db;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        title_layout = QtWidgets.QHBoxLayout(title_container)
        title_layout.setContentsMargins(20, 15, 20, 15)
        
        title_label = QtWidgets.QLabel("📚 Справка по работе с приложением")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        font = title_label.font()
        font.setPointSize(18)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
            }
        """)
        title_layout.addWidget(title_label)
        help_layout.addWidget(title_container)
        help_layout.addSpacing(20)
        
        # Добавляем разделы справки
        self.add_section(help_layout, "Общая информация", [
            "Приложение предназначено для работы с данными о фьючерсах FUSD.",
            "Основные функции приложения:",
            "• Просмотр и редактирование данных о торгах и датах исполнения",
            "• Анализ логарифма изменения цены фьючерса",
            "• Расчет статистических характеристик",
            "• Визуализация данных на графиках"
        ])
        
        self.add_section(help_layout, "Работа с таблицами", [
            "Раздел \"Таблица\" содержит три вкладки:",
            "1. Первая таблица (торги) - информация о торгах фьючерсами",
            "2. Вторая таблица (исполнения) - информация о датах исполнения фьючерсов",
            "3. Третья таблица (совмещённая) - объединенная информация о торгах и исполнениях",
            "",
            "Функции управления таблицами:",
            "• Добавить - добавление новой записи",
            "• Изменить - редактирование выбранной записи",
            "• Удалить - удаление записи или записей",
            "",
            "Для сортировки таблицы по разным полям используйте переключатель \"Сортировка\".",
            "Для быстрого анализа данных выделите строку в таблице - информация будет автоматически перенесена на вкладку \"Анализ\"."
        ])
        
        self.add_section(help_layout, "Анализ данных", [
            "Раздел \"Анализ\" позволяет рассчитать и визуализировать логарифм изменения цены фьючерса.",
            "",
            "Параметры анализа:",
            "• Период анализа - диапазон дат для проведения анализа (от и до)",
            "• Код фьючерса - выбор фьючерса для анализа из выпадающего списка",
            "• Период предыстории - фиксированное значение 365 дней (используется для расчета показателей)",
            "• Учитывать дни с контрактами = 0 - включить/исключить из анализа дни с нулевым объемом торгов",
            "",
            "Результаты анализа представлены в двух вкладках:",
            "1. График - визуализация изменения логарифма цены фьючерса",
            "2. Статистика - основные статистические характеристики",
            "",
            "Для экспорта отчета в PDF используйте кнопку \"Экспорт отчета\"."
        ])
        
        self.add_section(help_layout, "Формулы и показатели анализа", [
            "Анализ основан на расчете логарифма изменения цены фьючерса за два торговых дня.",
            "",
            "Основная формула:",
            "L(t) = ln(P(t) / P(t-2))",
            "где:",
            "• L(t) - логарифм изменения цены на дату t",
            "• P(t) - цена фьючерса на дату t",
            "• P(t-2) - цена фьючерса на дату t-2 (два торговых дня назад)",
            "• ln - натуральный логарифм",
            "",
            "Рассчитываемые статистические показатели:",
            "",
            "• Среднее значение (Mean):",
            "  μ = (1/N) × Σ L(i), где N - количество точек данных",
            "  Показывает среднее логарифмическое изменение цены за период.",
            "",
            "• Стандартное отклонение (Std Dev):",
            "  σ = √[(1/N) × Σ(L(i) - μ)²]",
            "  Характеризует волатильность (изменчивость) цены фьючерса.",
            "",
            "• Медиана (Median):",
            "  Значение, делящее отсортированный ряд данных пополам.",
            "  Устойчива к выбросам, показывает \"типичное\" изменение.",
            "",
            "• Минимальное и максимальное значения:",
            "  Крайние значения логарифма изменения цены в анализируемом периоде.",
            "",
            "• Размах (Range):",
            "  Range = Max - Min",
            "  Показывает диапазон колебаний показателя.",
            "",
            "• Коэффициент вариации (CV):",
            "  CV = (σ / |μ|) × 100%",
            "  Относительная мера изменчивости, позволяет сравнивать волатильность разных фьючерсов независимо от абсолютных значений цен.",
            "",
            "Тренды:",
            "Данные разбиваются на две половины, и сравниваются средние значения и дисперсии первой и второй половины периода:",
            "• Тренд среднего - растет/уменьшается/стабильно (порог изменения ±5%)",
            "• Тренд волатильности - растет/уменьшается/стабильно (порог изменения ±10%)",
            "",
            "Примечание:",
            "Для корректного расчета требуется минимум 3 торговых дня с данными о ценах.",
            "Чем больше точек данных, тем надежнее статистические оценки."
        ])
        
        self.add_section(help_layout, "Формат кода фьючерса", [
            "Код фьючерса имеет формат FUSD_MM_YY, где:",
            "• FUSD - префикс, обозначающий фьючерс на доллар США",
            "• MM - месяц исполнения (01-12)",
            "• YY - год исполнения (две последние цифры года в 20-м веке)",
            "",
            "Пример: FUSD_06_96 - фьючерс на доллар США с исполнением в июне 1996 года."
        ])
        
        self.add_section(help_layout, "Горячие клавиши", [
            "Tab - активация автодополнения кода фьючерса",
            "Enter - подтверждение ввода в диалогах",
            "Escape - отмена операции/закрытие диалога"
        ])
        
        # Добавляем виджет с содержимым в скроллируемую область
        scroll_area.setWidget(help_content)
        main_layout.addWidget(scroll_area)

    def add_section(self, layout, title, content_lines):
        """Добавляет раздел справки с заголовком и содержимым"""
        section_container = QtWidgets.QWidget()
        section_layout = QtWidgets.QVBoxLayout(section_container)
        section_layout.setContentsMargins(20, 15, 20, 15)
        section_layout.setSpacing(12)
        
        section_container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        section_title = QtWidgets.QLabel(title)
        font = section_title.font()
        font.setPointSize(15)
        font.setBold(True)
        section_title.setFont(font)
        section_title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 5px 0px;
                margin-bottom: 5px;
            }
        """)
        section_layout.addWidget(section_title)
        
        html_content = ""
        in_list = False
        
        for i, line in enumerate(content_lines):
            if not line.strip():
                if in_list:
                    html_content += "</ul><p style='margin: 8px 0;'></p>"
                    in_list = False
                else:
                    html_content += "<p style='margin: 8px 0;'></p>"
                continue
                
            if line.strip().startswith("•") or line.strip().startswith("-"):
                if not in_list:
                    html_content += "<ul style='margin: 10px 0; padding-left: 25px; line-height: 1.6;'>"
                    in_list = True
                item_text = line.strip()[1:].strip()
                html_content += f"<li style='margin-bottom: 6px; color: #34495e; overflow-wrap: break-word;'>{item_text}</li>"
                
            elif line.strip()[0].isdigit() and ". " in line[:5]:
                if not in_list:
                    html_content += "<ol style='margin: 10px 0; padding-left: 25px; line-height: 1.6;'>"
                    in_list = True
                item_text = line.strip()[line.find(".")+1:].strip()
                html_content += f"<li style='margin-bottom: 6px; color: #34495e; overflow-wrap: break-word;'>{item_text}</li>"
                
            else:
                if in_list:
                    if not (line.strip().startswith("•") or line.strip().startswith("-") or (line.strip()[0].isdigit() and ". " in line[:5])):
                        html_content += "</ul>"
                        in_list = False
                        if line.strip().startswith("где:") or line.strip().startswith("Тренды:") or line.strip().startswith("Примечание:"):
                            html_content += f"<p style='margin: 12px 0 8px 0; font-weight: bold; color: #2980b9;'>{line}</p>"
                        elif "=" in line and ("ln" in line or "L(" in line or "P(" in line or "μ" in line or "σ" in line):
                            html_content += f"<p style='margin: 8px 0; padding: 8px 12px; background-color: #ecf0f1; border-left: 4px solid #3498db; font-family: monospace; color: #2c3e50; word-wrap: break-word; overflow-wrap: break-word; white-space: pre-wrap;'>{line}</p>"
                        else:
                            html_content += f"<p style='margin: 8px 0; line-height: 1.6; color: #34495e;'>{line}</p>"
                else:
                    if line.strip().startswith("где:") or line.strip().startswith("Тренды:") or line.strip().startswith("Примечание:"):
                        html_content += f"<p style='margin: 12px 0 8px 0; font-weight: bold; color: #2980b9;'>{line}</p>"
                    elif "=" in line and ("ln" in line or "L(" in line or "P(" in line or "μ" in line or "σ" in line):
                        html_content += f"<p style='margin: 8px 0; padding: 8px 12px; background-color: #ecf0f1; border-left: 4px solid #3498db; font-family: monospace; color: #2c3e50; word-wrap: break-word; overflow-wrap: break-word; white-space: pre-wrap;'>{line}</p>"
                    else:
                        html_content += f"<p style='margin: 8px 0; line-height: 1.6; color: #34495e;'>{line}</p>"
        
        if in_list:
            html_content += "</ul>"
        
        content = QtWidgets.QLabel()
        content.setTextFormat(QtCore.Qt.RichText)
        content.setWordWrap(True)
        content.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse)
        content.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        content.setStyleSheet("""
            QLabel {
                background-color: transparent;
                padding: 5px;
            }
        """)
        
        html_content = f"<div style='width: 100%;'>{html_content}</div>"
        
        content.setText(html_content)
        section_layout.addWidget(content)
        
        layout.addWidget(section_container)
        layout.addSpacing(15)
