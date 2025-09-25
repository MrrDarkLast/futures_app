import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import Trade, Future
from db import SessionLocal


def get_trading_days(future_code: str, start_date: date, end_date: date) -> List[date]:
    """
    Получить список дат торгов для указанного фьючерса в заданном диапазоне дат.
    
    Args:
        future_code: Код фьючерса
        start_date: Начальная дата
        end_date: Конечная дата
        
    Returns:
        Список дат торгов
    """
    with SessionLocal() as session:
        query = (
            select(Trade.trade_date)
            .where(Trade.future_code == future_code)
            .where(Trade.trade_date >= start_date)
            .where(Trade.trade_date <= end_date)
            .order_by(Trade.trade_date)
        )
        result = session.execute(query).scalars().all()
        return result


def get_price_for_date(future_code: str, trade_date: date, session: Session) -> Optional[float]:
    """
    Получить цену фьючерса на указанную дату.
    
    Args:
        future_code: Код фьючерса
        trade_date: Дата торгов
        session: Сессия SQLAlchemy
        
    Returns:
        Цена фьючерса или None, если данных нет
    """
    query = (
        select(Trade.price_rub_per_usd)
        .where(Trade.future_code == future_code)
        .where(Trade.trade_date == trade_date)
    )
    result = session.execute(query).scalar_one_or_none()
    return float(result) if result is not None else None


def calculate_price_change(future_code: str, trade_date: date, history_days: int = 30) -> Dict:
    """
    Рассчитать логарифм изменения цены фьючерса за два торговых дня
    и статистические характеристики на основе предыстории.
    
    Args:
        future_code: Код фьючерса
        trade_date: Дата торгов
        history_days: Количество календарных дней предыстории
        
    Returns:
        Словарь с результатами расчетов
    """
    # Определяем начальную дату предыстории
    start_date = trade_date - timedelta(days=history_days)
    
    with SessionLocal() as session:
        # Получаем все даты торгов для данного фьючерса в указанном диапазоне
        trading_days = get_trading_days(future_code, start_date, trade_date)
        
        if not trading_days or len(trading_days) < 3:
            return {
                "future_code": future_code,
                "trade_date": trade_date,
                "error": "Недостаточно данных для расчета"
            }
            
        # Получаем цены для всех дат торгов
        prices = {}
        for day in trading_days:
            price = get_price_for_date(future_code, day, session)
            if price is not None:
                prices[day] = price
                
        if len(prices) < 3:
            return {
                "future_code": future_code,
                "trade_date": trade_date,
                "error": "Недостаточно данных о ценах для расчета"
            }
            
        # Сортируем даты торгов
        sorted_days = sorted(prices.keys())
        
        # Рассчитываем логарифм изменения цены для каждого дня (начиная с третьего)
        log_changes = []
        dates = []
        
        for i in range(2, len(sorted_days)):
            current_day = sorted_days[i]
            prev_day_2 = sorted_days[i-2]
            
            current_price = prices[current_day]
            prev_price_2 = prices[prev_day_2]
            
            if current_price > 0 and prev_price_2 > 0:
                log_change = np.log(current_price / prev_price_2)
                log_changes.append(log_change)
                dates.append(current_day)
                
        if not log_changes:
            return {
                "future_code": future_code,
                "trade_date": trade_date,
                "error": "Не удалось рассчитать логарифм изменения цены"
            }
            
        # Рассчитываем статистические характеристики
        mean_value = np.mean(log_changes)
        std_dev = np.std(log_changes)
        median = np.median(log_changes)
        min_value = np.min(log_changes)
        max_value = np.max(log_changes)
        
        # Определяем тенденцию изменения среднего значения и дисперсии
        # Разделяем данные на две половины и сравниваем
        half_idx = len(log_changes) // 2
        first_half = log_changes[:half_idx]
        second_half = log_changes[half_idx:]
        
        mean_trend = "стабильно"
        if len(first_half) > 0 and len(second_half) > 0:
            mean_first = np.mean(first_half)
            mean_second = np.mean(second_half)
            
            if mean_second > mean_first * 1.05:  # Увеличение более чем на 5%
                mean_trend = "растет"
            elif mean_second < mean_first * 0.95:  # Уменьшение более чем на 5%
                mean_trend = "уменьшается"
                
        variance_trend = "стабильно"
        if len(first_half) > 0 and len(second_half) > 0:
            var_first = np.var(first_half)
            var_second = np.var(second_half)
            
            if var_second > var_first * 1.1:  # Увеличение более чем на 10%
                variance_trend = "растет"
            elif var_second < var_first * 0.9:  # Уменьшение более чем на 10%
                variance_trend = "уменьшается"
                
        # Значение показателя для указанной даты
        current_value = None
        if trade_date in dates:
            idx = dates.index(trade_date)
            current_value = log_changes[idx]
            
        # Формируем результат
        result = {
            "future_code": future_code,
            "trade_date": trade_date,
            "current_value": current_value,
            "statistics": {
                "mean": mean_value,
                "std_dev": std_dev,
                "median": median,
                "min": min_value,
                "max": max_value,
                "count": len(log_changes)
            },
            "trends": {
                "mean": mean_trend,
                "variance": variance_trend
            },
            "data": {
                "dates": dates,
                "values": log_changes
            }
        }
        
        return result


def plot_price_changes(future_code: str, trade_date: date, history_days: int = 30, save_path: Optional[str] = None):
    """
    Построить график логарифма изменения цены фьючерса.
    
    Args:
        future_code: Код фьючерса
        trade_date: Дата торгов
        history_days: Количество календарных дней предыстории
        save_path: Путь для сохранения графика (если None, то график будет показан)
    """
    result = calculate_price_change(future_code, trade_date, history_days)
    
    if "error" in result:
        print(f"Ошибка: {result['error']}")
        return
        
    dates = result["data"]["dates"]
    values = result["data"]["values"]
    
    plt.figure(figsize=(12, 6))
    
    # График логарифма изменения цены
    plt.subplot(1, 2, 1)
    plt.plot(dates, values, 'b-', marker='o')
    plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
    plt.title(f'Логарифм изменения цены фьючерса {future_code}')
    plt.xlabel('Дата')
    plt.ylabel('ln(F(t)/F(t-2))')
    plt.grid(True)
    
    # Форматируем даты на оси X в формате DD-MM-YYYY
    import matplotlib.dates as mdates
    date_format = mdates.DateFormatter('%d-%m-%Y')
    plt.gca().xaxis.set_major_formatter(date_format)
    
    plt.xticks(rotation=45, ha='right')
    
    # Гистограмма распределения
    plt.subplot(1, 2, 2)
    plt.hist(values, bins=10, alpha=0.7, color='blue')
    plt.axvline(result["statistics"]["mean"], color='r', linestyle='--', label=f'Среднее: {result["statistics"]["mean"]:.4f}')
    plt.axvline(result["statistics"]["median"], color='g', linestyle='--', label=f'Медиана: {result["statistics"]["median"]:.4f}')
    plt.title('Распределение логарифма изменения цены')
    plt.xlabel('ln(F(t)/F(t-2))')
    plt.ylabel('Частота')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()
        
    plt.close()


def generate_report(future_code: str, trade_date: date, history_days: int = 30) -> str:
    """
    Сгенерировать текстовый отчет о логарифме изменения цены фьючерса.
    
    Args:
        future_code: Код фьючерса
        trade_date: Дата торгов
        history_days: Количество календарных дней предыстории
        
    Returns:
        Текстовый отчет
    """
    result = calculate_price_change(future_code, trade_date, history_days)
    
    if "error" in result:
        return f"Ошибка: {result['error']}"
        
    stats = result["statistics"]
    trends = result["trends"]
    
    report = f"""ОТЧЕТ ПО АНАЛИЗУ ИЗМЕНЕНИЯ ЦЕНЫ ФЬЮЧЕРСА
======================================

Код фьючерса: {future_code}
Дата анализа: {trade_date.strftime('%d-%m-%Y')}
Период предыстории: {history_days} календарных дней

СТАТИСТИЧЕСКИЕ ХАРАКТЕРИСТИКИ:
-----------------------------
Количество торговых дней: {stats['count']}
(Число дней, за которые есть данные о торгах по выбранному фьючерсу в заданном периоде предыстории)

Среднее значение ln(F(t)/F(t-2)): {stats['mean']:.6f}
Стандартное отклонение: {stats['std_dev']:.6f}
Медиана: {stats['median']:.6f}
Минимальное значение: {stats['min']:.6f}
Максимальное значение: {stats['max']:.6f}

ТЕНДЕНЦИИ ИЗМЕНЕНИЯ:
-------------------
Среднее значение: {trends['mean']}
Дисперсия: {trends['variance']}

"""
    
    if result["current_value"] is not None:
        report += f"""ТЕКУЩЕЕ ЗНАЧЕНИЕ:
----------------
ln(F(t)/F(t-2)) на {trade_date.strftime('%d-%m-%Y')}: {result['current_value']:.6f}
"""
    
    return report


def analyze_all_futures(trade_date: date, history_days: int = 30, sort_by_code: bool = True) -> Dict:
    """
    Проанализировать все фьючерсы, торговавшиеся в указанную дату.
    
    Args:
        trade_date: Дата торгов
        history_days: Количество календарных дней предыстории
        sort_by_code: Сортировать ли результаты по коду фьючерса
        
    Returns:
        Словарь с результатами анализа по каждому фьючерсу
    """
    with SessionLocal() as session:
        # Получаем все фьючерсы, торговавшиеся в указанную дату
        query = (
            select(Trade.future_code)
            .where(Trade.trade_date == trade_date)
        )
        
        # Добавляем сортировку по коду, если требуется
        if sort_by_code:
            query = query.order_by(Trade.future_code)
            
        query = query.distinct()
        futures = session.execute(query).scalars().all()
        
        results = {}
        for future_code in futures:
            results[future_code] = calculate_price_change(future_code, trade_date, history_days)
            
        return results
