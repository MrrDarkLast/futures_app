import numpy as np
from datetime import date, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from models import Trade
from db import SessionLocal


def get_trading_days(
    future_code: str,
    start_date: date,
    end_date: date,
    include_zero_contracts: bool = True,
    contracts_from: Optional[int] = None,
    contracts_to: Optional[int] = None,
    price_from: Optional[float] = None,
    price_to: Optional[float] = None
) -> List[date]:
    """
    Получить список дат торгов для указанного фьючерса в заданном диапазоне дат.
    
    Args:
        future_code: Код фьючерса
        start_date: Начальная дата
        end_date: Конечная дата
        include_zero_contracts: Включать ли дни с контрактами = 0
        contracts_from: Минимальное количество контрактов (None = без ограничения)
        contracts_to: Максимальное количество контрактов (None = без ограничения)
        price_from: Минимальная цена (None = без ограничения)
        price_to: Максимальная цена (None = без ограничения)
        
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
        
        if not include_zero_contracts:
            query = query.where(
                or_(Trade.contracts_count.is_(None), Trade.contracts_count != 0)
            )
        
        if contracts_from is not None:
            query = query.where(
                or_(Trade.contracts_count.is_(None), Trade.contracts_count >= contracts_from)
            )
        
        if contracts_to is not None:
            query = query.where(
                or_(Trade.contracts_count.is_(None), Trade.contracts_count <= contracts_to)
            )
        
        if price_from is not None:
            query = query.where(Trade.price_rub_per_usd >= price_from)
        
        if price_to is not None:
            query = query.where(Trade.price_rub_per_usd <= price_to)
        
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


def calculate_price_change(
    future_code: str,
    trade_date: date,
    history_days: int = 30,
    include_zero_contracts: bool = True,
    contracts_from: Optional[int] = None,
    contracts_to: Optional[int] = None,
    price_from: Optional[float] = None,
    price_to: Optional[float] = None
) -> Dict:
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
        trading_days = get_trading_days(
            future_code,
            start_date,
            trade_date,
            include_zero_contracts=include_zero_contracts,
            contracts_from=contracts_from,
            contracts_to=contracts_to,
            price_from=price_from,
            price_to=price_to
        )
        
        if not trading_days or len(trading_days) < 3:
            trading_days_count = len(trading_days) if trading_days else 0
            error_msg = f"Недостаточно данных для расчета\n"
            error_msg += f"Найдено торговых дней: {trading_days_count}\n"
            error_msg += f"Требуется минимум: 3 торговых дня"
            
            return {
                "future_code": future_code,
                "trade_date": trade_date,
                "error": error_msg
            }
            
        # Получаем цены для всех дат торгов
        prices = {}
        for day in trading_days:
            price = get_price_for_date(future_code, day, session)
            if price is not None:
                prices[day] = price
                
        if len(prices) < 3:
            error_msg = f"Недостаточно данных о ценах для расчета\n"
            error_msg += f"Найдено цен: {len(prices)}\n"
            error_msg += f"Требуется минимум: 3 цены"
            
            return {
                "future_code": future_code,
                "trade_date": trade_date,
                "error": error_msg
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


