import unittest
import os
import sys
from datetime import date
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Добавляем корневую директорию проекта в sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Base, Future, Expiration, Trade
from services import delete_trades_by_date


class TestServices(unittest.TestCase):
    """Тесты для сервисных функций"""

    def setUp(self):
        """Создание тестовой базы данных перед каждым тестом"""
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        
        # Создаем тестовые данные
        future = Future(code="FUSD_03_98", name="Тестовый фьючерс")
        self.session.add(future)
        
        expiry_date = date(1998, 3, 15)
        expiration = Expiration(future_code="FUSD_03_98", expiry_date=expiry_date)
        self.session.add(expiration)
        
        trade_date = date(1998, 2, 10)
        trade = Trade(
            trade_date=trade_date,
            future_code="FUSD_03_98",
            price_rub_per_usd=25.5,
            contracts_count=100
        )
        self.session.add(trade)
        self.session.commit()

    def tearDown(self):
        """Закрытие сессии после каждого теста"""
        self.session.close()

    def test_delete_trades_by_date(self):
        """Тест удаления торгов по дате"""
        # Добавим еще одну запись с другой датой
        trade_date2 = date(1998, 2, 11)
        trade2 = Trade(
            trade_date=trade_date2,
            future_code="FUSD_03_98",
            price_rub_per_usd=26.0,
            contracts_count=200
        )
        self.session.add(trade2)
        self.session.commit()
        
        # Проверяем, что у нас две записи
        count_before = self.session.query(Trade).count()
        self.assertEqual(count_before, 2)
        
        # Удаляем записи за 10.02.1998
        delete_date = date(1998, 2, 10)
        
        # Создаем мок-объект для SessionLocal
        mock_session = MagicMock()
        mock_session.return_value.__enter__.return_value = self.session
        mock_session.return_value.__exit__.return_value = None
        
        # Патчим функцию begin() сессии, чтобы избежать ошибки "транзакция уже начата"
        with patch('services.SessionLocal', mock_session):
            with patch.object(self.session, 'begin', return_value=MagicMock()):
                deleted_count = delete_trades_by_date(delete_date)
                
        # Проверяем, что удалена одна запись
        self.assertEqual(self.session.query(Trade).count(), 1)
        
        # Проверяем, что осталась только запись за 11.02.1998
        remaining_trade = self.session.query(Trade).first()
        self.assertEqual(remaining_trade.trade_date, trade_date2)
        
    def test_delete_trades_by_date_with_codes(self):
        """Тест удаления торгов по дате с фильтрацией по кодам"""
        # Добавим еще одну запись с тем же днем, но другим кодом
        future2 = Future(code="FUSD_04_98", name="Тестовый фьючерс 2")
        self.session.add(future2)
        self.session.flush()
        
        trade_date = date(1998, 2, 10)
        trade2 = Trade(
            trade_date=trade_date,
            future_code="FUSD_04_98",
            price_rub_per_usd=26.0,
            contracts_count=200
        )
        self.session.add(trade2)
        self.session.commit()
        
        # Проверяем, что у нас две записи
        count_before = self.session.query(Trade).count()
        self.assertEqual(count_before, 2)
        
        # Удаляем записи за 10.02.1998 только для кода FUSD_03_98
        delete_date = date(1998, 2, 10)
        
        # Создаем мок-объект для SessionLocal
        mock_session = MagicMock()
        mock_session.return_value.__enter__.return_value = self.session
        mock_session.return_value.__exit__.return_value = None
        
        # Патчим функцию begin() сессии, чтобы избежать ошибки "транзакция уже начата"
        with patch('services.SessionLocal', mock_session):
            with patch.object(self.session, 'begin', return_value=MagicMock()):
                delete_trades_by_date(delete_date, ["FUSD_03_98"])
        
        # Проверяем, что осталась только запись с кодом FUSD_04_98
        remaining_trade = self.session.query(Trade).first()
        self.assertEqual(remaining_trade.future_code, "FUSD_04_98")


if __name__ == '__main__':
    unittest.main()