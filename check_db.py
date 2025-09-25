#!/usr/bin/env python
from db import SessionLocal
from sqlalchemy import select
from models import Trade, Future, Expiration

def check_database():
    """Проверить наличие данных в базе данных"""
    with SessionLocal() as s:
        # Проверяем наличие фьючерсов
        futures = s.execute(select(Future.code)).scalars().all()
        print(f"Futures in database: {len(futures)}")
        print(f"Sample futures: {futures[:5] if futures else 'No futures'}")
        
        # Проверяем наличие дат исполнения
        expirations = s.execute(select(Expiration.future_code, Expiration.expiry_date)).all()
        print(f"\nExpirations in database: {len(expirations)}")
        print(f"Sample expirations: {expirations[:5] if expirations else 'No expirations'}")
        
        # Проверяем наличие торгов
        trades = s.execute(select(Trade.future_code, Trade.trade_date, Trade.price_rub_per_usd)).all()
        print(f"\nTrades in database: {len(trades)}")
        print(f"Sample trades: {trades[:5] if trades else 'No trades'}")
        
        # Проверяем наличие торгов для каждого фьючерса
        if futures and trades:
            for future_code in futures:
                future_trades = s.execute(
                    select(Trade.trade_date)
                    .where(Trade.future_code == future_code)
                    .order_by(Trade.trade_date)
                ).scalars().all()
                print(f"\nTrades for {future_code}: {len(future_trades)}")
                if future_trades:
                    print(f"First trade date: {future_trades[0]}")
                    print(f"Last trade date: {future_trades[-1]}")
                    
                    # Проверяем, есть ли достаточно данных для расчета логарифма изменения цены
                    if len(future_trades) >= 3:
                        print(f"Has enough data for price change calculation: YES")
                    else:
                        print(f"Has enough data for price change calculation: NO (need at least 3 trading days)")

if __name__ == "__main__":
    check_database()
