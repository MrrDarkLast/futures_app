from datetime import date, datetime
import re
from typing import List, Optional, Tuple

from services import ValidationError


class FuturesValidator:
    """Класс для валидации данных фьючерсов"""
    
    # Регулярное выражение для проверки формата кода фьючерса FUSD_MM_YY
    CODE_PATTERN = re.compile(r'^FUSD_(\d{2})_(\d{2})$')
    
    @classmethod
    def validate_future_code(cls, code: str) -> Tuple[bool, List[str]]:
        """
        Проверяет корректность кода фьючерса
        
        Args:
            code: Код фьючерса для проверки
            
        Returns:
            Tuple[bool, List[str]]: (результат валидации, список ошибок)
        """
        errors = []
        
        if not code:
            errors.append("Код фьючерса не может быть пустым")
            return False, errors
        
        if not code.startswith("FUSD_"):
            errors.append(f"Код {code} должен начинаться с префикса FUSD_")
            return False, errors
            
        # Проверка полного формата кода FUSD_MM_YY
        match = cls.CODE_PATTERN.match(code)
        if not match:
            errors.append(f"Код {code} не соответствует формату FUSD_MM_YY")
            return False, errors
            
        # Проверка корректности месяца
        month = int(match.group(1))
        if month < 1 or month > 12:
            errors.append(f"Месяц в коде ({month}) должен быть от 1 до 12")
            return False, errors
            
        return len(errors) == 0, errors
        
    @classmethod
    def validate_code_exists(cls, code: str, session) -> Tuple[bool, List[str]]:
        """
        Проверяет, что код фьючерса существует в базе данных
        
        Args:
            code: Код фьючерса для проверки
            session: Сессия SQLAlchemy для доступа к базе данных
            
        Returns:
            Tuple[bool, List[str]]: (результат валидации, список ошибок)
        """
        from models import Expiration
        
        errors = []
        
        # Проверяем формат кода
        valid, format_errors = cls.validate_future_code(code)
        if not valid:
            return valid, format_errors
            
        # Проверяем существование кода в базе данных
        from sqlalchemy import select
        result = session.execute(select(Expiration).where(Expiration.future_code == code))
        expiration = result.scalars().first()
        
        if expiration is None:
            errors.append(f"Код {code} не существует в базе данных.")
            return False, errors
            
        return True, []
    
    @classmethod
    def format_date(cls, d: date) -> str:
        """Форматирует дату в формат DD-MM-YYYY"""
        return d.strftime("%d-%m-%Y")
    
    @classmethod
    def validate_expiry_date(cls, expiry_date: date) -> Tuple[bool, List[str]]:
        """
        Проверяет корректность даты исполнения
        
        Args:
            expiry_date: Дата исполнения для проверки
            
        Returns:
            Tuple[bool, List[str]]: (результат валидации, список ошибок)
        """
        errors = []
        
        if not expiry_date:
            errors.append("Дата исполнения не может быть пустой")
            return False, errors
        
        # Для фьючерсов дата исполнения может быть в прошлом (для исторических данных)
        # Здесь мы не проверяем, что дата не в прошлом, так как это допустимо
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_code_expiry_match(cls, code: str, expiry_date: date) -> Tuple[bool, List[str]]:
        """
        Проверяет соответствие кода фьючерса и даты исполнения
        
        Args:
            code: Код фьючерса
            expiry_date: Дата исполнения
            
        Returns:
            Tuple[bool, List[str]]: (результат валидации, список ошибок)
        """
        errors = []
        
        if not code or not expiry_date:
            return False, ["Код и дата исполнения должны быть указаны"]
            
        match = cls.CODE_PATTERN.match(code)
        if not match:
            return False, [f"Код {code} не соответствует формату FUSD_MM_YY"]
            
        code_month = int(match.group(1))
        year_2digit = int(match.group(2))
        # Правило окна: 00-49 = 20XX, 50-99 = 19XX
        code_year = 2000 + year_2digit if year_2digit < 50 else 1900 + year_2digit
        
        # Проверяем соответствие месяца и года в коде с датой исполнения
        if code_month != expiry_date.month:
            errors.append(f"Месяц в коде ({code_month}) не соответствует месяцу даты исполнения ({expiry_date.month})")
            
        if code_year != expiry_date.year:
            errors.append(f"Год в коде ({code_year}) не соответствует году даты исполнения ({expiry_date.year})")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_trade_date(cls, trade_date: date, expiry_date: Optional[date] = None) -> Tuple[bool, List[str]]:
        """
        Проверяет корректность даты торговли
        
        Args:
            trade_date: Дата торговли
            expiry_date: Дата исполнения (опционально)
            
        Returns:
            Tuple[bool, List[str]]: (результат валидации, список ошибок)
        """
        errors = []
        
        if not trade_date:
            errors.append("Дата торговли не может быть пустой")
            return False, errors
            
        # Дата торговли не должна быть в будущем
        today = date.today()
        if trade_date > today:
            errors.append(f"Дата торговли ({cls.format_date(trade_date)}) не может быть в будущем")
            
        # Дата торговли не должна быть позже даты исполнения
        if expiry_date and trade_date > expiry_date:
            errors.append(
                f"Дата торговли ({cls.format_date(trade_date)}) не может быть позже "
                f"даты исполнения ({cls.format_date(expiry_date)})"
            )
            
        return len(errors) == 0, errors
    
    @classmethod
    def validate_price(cls, price: float) -> Tuple[bool, List[str]]:
        """
        Проверяет корректность цены
        
        Args:
            price: Цена для проверки
            
        Returns:
            Tuple[bool, List[str]]: (результат валидации, список ошибок)
        """
        errors = []
        
        if price <= 0:
            errors.append(f"Цена ({price}) должна быть больше нуля")
            
        return len(errors) == 0, errors
    
    @classmethod
    def validate_contracts_count(cls, contracts: Optional[int]) -> Tuple[bool, List[str]]:
        """
        Проверяет корректность количества контрактов
        
        Args:
            contracts: Количество контрактов для проверки
            
        Returns:
            Tuple[bool, List[str]]: (результат валидации, список ошибок)
        """
        errors = []
        
        if contracts is None:
            errors.append("Количество контрактов не может быть пустым")
            return False, errors
            
        if contracts < 0:
            errors.append(f"Количество контрактов ({contracts}) не может быть отрицательным")
            
        return len(errors) == 0, errors
    
    @classmethod
    def validate_trade(cls, trade_date: date, code: str, price: float, 
                       contracts: Optional[int], expiry_date: Optional[date] = None) -> Tuple[bool, List[str]]:
        """
        Полная валидация торговой записи
        
        Args:
            trade_date: Дата торговли
            code: Код фьючерса
            price: Цена
            contracts: Количество контрактов
            expiry_date: Дата исполнения (опционально)
            
        Returns:
            Tuple[bool, List[str]]: (результат валидации, список ошибок)
        """
        errors = []
        
        # Проверяем код фьючерса
        valid, code_errors = cls.validate_future_code(code)
        if not valid:
            errors.extend(code_errors)
        
        # Проверяем дату торговли
        valid, date_errors = cls.validate_trade_date(trade_date, expiry_date)
        if not valid:
            errors.extend(date_errors)
        
        # Проверяем цену
        valid, price_errors = cls.validate_price(price)
        if not valid:
            errors.extend(price_errors)
        
        # Проверяем количество контрактов
        valid, contracts_errors = cls.validate_contracts_count(contracts)
        if not valid:
            errors.extend(contracts_errors)
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_expiration(cls, code: str, expiry_date: date) -> Tuple[bool, List[str]]:
        """
        Полная валидация записи о дате исполнения
        
        Args:
            code: Код фьючерса
            expiry_date: Дата исполнения
            
        Returns:
            Tuple[bool, List[str]]: (результат валидации, список ошибок)
        """
        errors = []
        
        # Проверяем код фьючерса
        valid, code_errors = cls.validate_future_code(code)
        if not valid:
            errors.extend(code_errors)
        
        # Проверяем дату исполнения
        valid, expiry_errors = cls.validate_expiry_date(expiry_date)
        if not valid:
            errors.extend(expiry_errors)
        
        # Проверяем соответствие кода и даты исполнения
        valid, match_errors = cls.validate_code_expiry_match(code, expiry_date)
        if not valid:
            errors.extend(match_errors)
        
        return len(errors) == 0, errors
