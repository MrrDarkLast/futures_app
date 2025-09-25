import unittest
import os
import sys
from datetime import date

# Добавляем корневую директорию проекта в sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Base, Future, Expiration, Trade


class TestModels(unittest.TestCase):
    """Тесты для моделей данных"""

    def setUp(self):
        """Создание тестовой базы данных перед каждым тестом"""
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        """Закрытие сессии после каждого теста"""
        self.session.close()

    def test_future_creation(self):
        """Тест создания записи фьючерса"""
        future = Future(code="FUSD_03_98", name="Тестовый фьючерс")
        self.session.add(future)
        self.session.commit()

        # Проверяем, что запись создана
        result = self.session.query(Future).filter_by(code="FUSD_03_98").first()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Тестовый фьючерс")

    def test_expiration_creation(self):
        """Тест создания записи даты исполнения"""
        # Сначала создаем фьючерс
        future = Future(code="FUSD_03_98", name="Тестовый фьючерс")
        self.session.add(future)
        self.session.flush()

        # Создаем дату исполнения
        expiry_date = date(1998, 3, 15)
        expiration = Expiration(future_code="FUSD_03_98", expiry_date=expiry_date)
        self.session.add(expiration)
        self.session.commit()

        # Проверяем, что запись создана
        result = self.session.query(Expiration).filter_by(future_code="FUSD_03_98").first()
        self.assertIsNotNone(result)
        self.assertEqual(result.expiry_date, expiry_date)

        # Проверяем связь с фьючерсом
        self.assertEqual(result.future.code, "FUSD_03_98")
        self.assertEqual(result.future.name, "Тестовый фьючерс")

    def test_trade_creation(self):
        """Тест создания записи торга"""
        # Создаем фьючерс
        future = Future(code="FUSD_03_98", name="Тестовый фьючерс")
        self.session.add(future)
        self.session.flush()

        # Создаем дату исполнения
        expiry_date = date(1998, 3, 15)
        expiration = Expiration(future_code="FUSD_03_98", expiry_date=expiry_date)
        self.session.add(expiration)
        self.session.flush()

        # Создаем торг
        trade_date = date(1998, 2, 10)
        trade = Trade(
            trade_date=trade_date,
            future_code="FUSD_03_98",
            price_rub_per_usd=25.5,
            contracts_count=100
        )
        self.session.add(trade)
        self.session.commit()

        # Проверяем, что запись создана
        result = self.session.query(Trade).filter_by(
            trade_date=trade_date, 
            future_code="FUSD_03_98"
        ).first()
        self.assertIsNotNone(result)
        self.assertEqual(float(result.price_rub_per_usd), 25.5)
        self.assertEqual(result.contracts_count, 100)

        # Проверяем связь с фьючерсом
        self.assertEqual(result.future.code, "FUSD_03_98")

    def test_cascade_delete(self):
        """Тест каскадного удаления"""
        # Создаем фьючерс
        future = Future(code="FUSD_03_98", name="Тестовый фьючерс")
        self.session.add(future)
        self.session.flush()

        # Создаем дату исполнения
        expiry_date = date(1998, 3, 15)
        expiration = Expiration(future_code="FUSD_03_98", expiry_date=expiry_date)
        self.session.add(expiration)
        self.session.flush()

        # Создаем торг
        trade_date = date(1998, 2, 10)
        trade = Trade(
            trade_date=trade_date,
            future_code="FUSD_03_98",
            price_rub_per_usd=25.5,
            contracts_count=100
        )
        self.session.add(trade)
        self.session.commit()

        # Удаляем фьючерс
        self.session.delete(future)
        self.session.commit()

        # Проверяем, что все связанные записи удалены
        self.assertIsNone(self.session.query(Future).filter_by(code="FUSD_03_98").first())
        self.assertIsNone(self.session.query(Expiration).filter_by(future_code="FUSD_03_98").first())
        self.assertIsNone(self.session.query(Trade).filter_by(future_code="FUSD_03_98").first())

    def test_unique_constraint(self):
        """Тест ограничения уникальности для торгов"""
        # Создаем фьючерс
        future = Future(code="FUSD_03_98", name="Тестовый фьючерс")
        self.session.add(future)
        self.session.flush()

        # Создаем торг
        trade_date = date(1998, 2, 10)
        trade1 = Trade(
            trade_date=trade_date,
            future_code="FUSD_03_98",
            price_rub_per_usd=25.5,
            contracts_count=100
        )
        self.session.add(trade1)
        self.session.commit()

        # Пытаемся создать торг с такой же датой и кодом
        trade2 = Trade(
            trade_date=trade_date,
            future_code="FUSD_03_98",
            price_rub_per_usd=26.0,
            contracts_count=200
        )
        self.session.add(trade2)
        
        # Должно возникнуть исключение из-за нарушения ограничения уникальности
        with self.assertRaises(Exception):
            self.session.commit()


if __name__ == '__main__':
    unittest.main()
