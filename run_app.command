#!/bin/bash
# Скрипт для запуска приложения Futures DB

# Переходим в директорию скрипта
cd "$(dirname "$0")"

# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем приложение
python app.py
