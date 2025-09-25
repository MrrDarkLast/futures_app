from services import init_db, import_expirations_xls, import_trades_xls

# Инициализация базы данных
init_db()
print("База данных создана")

# Импорт данных из Excel
import_expirations_xls("data/dataisp.XLS", mode="upsert")
print("Даты исполнения импортированы")

import_trades_xls("data/F_usd.XLS", mode="upsert")
print("Торги импортированы")

print("Инициализация базы данных завершена")

