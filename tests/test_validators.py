import unittest
from datetime import date, timedelta

import sys
import os

# Добавляем корневую директорию проекта в sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from validators import FuturesValidator


class TestFuturesValidator(unittest.TestCase):
    """Тесты для класса FuturesValidator"""

    def test_validate_future_code_valid(self):
        """Тест валидации корректного кода фьючерса"""
        valid_codes = ["FUSD_01_98", "FUSD_12_99"]
        for code in valid_codes:
            with self.subTest(code=code):
                valid, errors = FuturesValidator.validate_future_code(code)
                self.assertTrue(valid)
                self.assertEqual(len(errors), 0)

    def test_validate_future_code_invalid(self):
        """Тест валидации некорректного кода фьючерса"""
        invalid_codes = [
            "",  # пустой код
            "FUSD",  # без суффикса
            "FUSD_",  # неполный код
            "FUSD_1_98",  # неверный формат месяца
            "FUSD_13_98",  # некорректный месяц
            "FUSD_00_98",  # некорректный месяц
            "FUSD_01_9",  # неверный формат года
            "USD_01_98",  # неверный префикс
        ]
        for code in invalid_codes:
            with self.subTest(code=code):
                valid, errors = FuturesValidator.validate_future_code(code)
                self.assertFalse(valid)
                self.assertGreater(len(errors), 0)

    def test_validate_expiry_date(self):
        """Тест валидации даты исполнения"""
        # Валидная дата
        valid_date = date(1998, 3, 15)
        valid, errors = FuturesValidator.validate_expiry_date(valid_date)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

        # Пустая дата
        invalid, errors = FuturesValidator.validate_expiry_date(None)
        self.assertFalse(invalid)
        self.assertGreater(len(errors), 0)

    def test_validate_code_expiry_match(self):
        """Тест проверки соответствия кода и даты исполнения"""
        # Корректное соответствие
        code = "FUSD_03_98"
        expiry_date = date(1998, 3, 15)
        valid, errors = FuturesValidator.validate_code_expiry_match(code, expiry_date)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

        # Несоответствие месяца
        code = "FUSD_04_98"
        expiry_date = date(1998, 3, 15)
        valid, errors = FuturesValidator.validate_code_expiry_match(code, expiry_date)
        self.assertFalse(valid)
        self.assertIn("месяц", errors[0].lower())

        # Несоответствие года
        code = "FUSD_03_99"
        expiry_date = date(1998, 3, 15)
        valid, errors = FuturesValidator.validate_code_expiry_match(code, expiry_date)
        self.assertFalse(valid)
        self.assertIn("год", errors[0].lower())

    def test_validate_trade_date(self):
        """Тест валидации даты торговли"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        expiry_date = today + timedelta(days=30)

        # Валидная дата (вчера)
        valid, errors = FuturesValidator.validate_trade_date(yesterday, expiry_date)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

        # Дата в будущем
        valid, errors = FuturesValidator.validate_trade_date(tomorrow, expiry_date)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("будущем", errors[0].lower())

        # Дата после даты исполнения
        late_date = expiry_date + timedelta(days=1)
        valid, errors = FuturesValidator.validate_trade_date(late_date, expiry_date)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)
        # Проверяем, что ошибка содержит упоминание о дате исполнения
        self.assertIn("дат", errors[0].lower())

    def test_validate_price(self):
        """Тест валидации цены"""
        # Валидная цена
        valid, errors = FuturesValidator.validate_price(25.5)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

        # Нулевая цена
        valid, errors = FuturesValidator.validate_price(0)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)

        # Отрицательная цена
        valid, errors = FuturesValidator.validate_price(-10)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)

    def test_validate_contracts_count(self):
        """Тест валидации количества контрактов"""
        # Валидное количество
        valid, errors = FuturesValidator.validate_contracts_count(100)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

        # Нулевое количество (допустимо)
        valid, errors = FuturesValidator.validate_contracts_count(0)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

        # None (допустимо)
        valid, errors = FuturesValidator.validate_contracts_count(None)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

        # Отрицательное количество
        valid, errors = FuturesValidator.validate_contracts_count(-10)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)


if __name__ == '__main__':
    unittest.main()
