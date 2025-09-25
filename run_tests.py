#!/usr/bin/env python
import unittest
import sys

if __name__ == '__main__':
    # Обнаружение и запуск всех тестов
    test_suite = unittest.defaultTestLoader.discover('tests')
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Возвращаем код ошибки, если тесты не прошли
    sys.exit(not result.wasSuccessful())
