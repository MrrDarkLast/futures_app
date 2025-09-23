from datetime import date
from typing import Iterable, Literal
import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from futures_app.db import SessionLocal, ENGINE
from futures_app.models import Base, Future, Expiration, Trade


def init_db():
    Base.metadata.create_all(ENGINE)

class ValidationError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors

def _clean_code(v) -> str:
    return str(v).strip()

# ---- Expirations ----
def _validate_expirations_df(df: pd.DataFrame) -> pd.DataFrame:
    fmtA = {"Фk", "Tk"}
    fmtB = {"kod", "exec_date"}
    cols = set(df.columns)

    if fmtA.issubset(cols):
        df = df.copy()
        df["code"] = df["Фk"].astype(str).str.strip()
        df["expiry_date"] = pd.to_datetime(df["Tk"], errors="coerce").dt.date
    elif fmtB.issubset(cols):
        df = df.copy()
        df["code"] = df["kod"].astype(str).str.strip()
        df["expiry_date"] = pd.to_datetime(df["exec_date"], errors="coerce").dt.date
    else:
        raise ValidationError([f"DATAISP: неизвестные колонки {sorted(cols)}"])

    if df["code"].isna().any() or (df["code"] == "").any():
        raise ValidationError(["DATAISP: пустой код фьючерса."])
    if df["expiry_date"].isna().any():
        raise ValidationError(["DATAISP: неверный формат даты исполнения."])
    if df.duplicated(["code"]).any():
        raise ValidationError(["DATAISP: дубликаты кодов."])

    return df[["code", "expiry_date"]]

# ---- Trades ----
def _validate_trades_df(df: pd.DataFrame) -> pd.DataFrame:
    fmtA = {"date", "Фk", "Fk", "Vk"}
    fmtB = {"torg_date", "kod", "quotation", "num_contr"}
    cols = set(df.columns)

    if fmtA.issubset(cols):
        df = df.copy()
        df["trade_date"]  = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["future_code"] = df["Фk"].astype(str).str.strip()
        df["price"]       = pd.to_numeric(df["Fk"], errors="coerce")
        df["volume"]      = pd.to_numeric(df["Vk"], errors="coerce")
        df["contracts"]   = None
    elif fmtB.issubset(cols):
        df = df.copy()
        df["trade_date"]  = pd.to_datetime(df["torg_date"], errors="coerce").dt.date
        df["future_code"] = df["kod"].astype(str).str.strip()
        df["price"]       = pd.to_numeric(df["quotation"], errors="coerce")
        df["contracts"]   = pd.to_numeric(df["num_contr"], errors="coerce")
        df["volume"]      = None
    else:
        raise ValidationError([f"F_USD: неизвестные колонки {sorted(cols)}"])

    if df["trade_date"].isna().any():
        raise ValidationError(["F_USD: неверный формат даты."])
    if df["future_code"].isna().any() or (df["future_code"] == "").any():
        raise ValidationError(["F_USD: пустой код."])
    if (df["price"] <= 0).any() or df["price"].isna().any():
        raise ValidationError(["F_USD: цена должна быть > 0."])
    if "contracts" in df and df["contracts"] is not None and (df["contracts"] < 0).any():
        raise ValidationError(["F_USD: число контрактов >= 0."])

    if df.duplicated(["trade_date", "future_code"]).any():
        raise ValidationError(["F_USD: дубликаты (дата, код)."])

    return df[["trade_date", "future_code", "price", "volume", "contracts"]]

# ---- Импорт ----
def import_expirations_xls(path: str, mode: Literal["insert","upsert"]="upsert"):
    df = _validate_expirations_df(pd.read_excel(path))
    with SessionLocal() as s, s.begin():
        codes = df["code"].unique().tolist()
        existing_codes = set(s.scalars(select(Future.code).where(Future.code.in_(codes))))
        for code in codes:
            if code not in existing_codes:
                s.add(Future(code=code))
        for row in df.itertuples(index=False):
            exp = s.get(Expiration, row.code)
            if exp is None:
                s.add(Expiration(future_code=row.code, expiry_date=row.expiry_date))
            elif mode == "upsert":
                exp.expiry_date = row.expiry_date

def import_trades_xls(path: str, mode: Literal["insert","upsert","replace"]="upsert"):
    df = _validate_trades_df(pd.read_excel(path))
    with SessionLocal() as s, s.begin():
        for r in df.itertuples(index=False):
            t = s.get(Trade, {"trade_date": r.trade_date, "future_code": r.future_code})
            if t is None:
                s.add(Trade(
                    trade_date=r.trade_date,
                    future_code=r.future_code,
                    price_rub_per_usd=r.price,
                    volume_mln_rub=None if r.volume is None else r.volume,
                    contracts_count=None if r.contracts is None else int(r.contracts)
                ))
            elif mode in ("upsert","replace"):
                t.price_rub_per_usd = r.price
                t.volume_mln_rub = None if r.volume is None else r.volume
                t.contracts_count = None if r.contracts is None else int(r.contracts)

def delete_trades_by_date(day: date, futures: Iterable[str] | None = None) -> int:
    with SessionLocal() as s, s.begin():
        q = delete(Trade).where(Trade.trade_date == day)
        if futures:
            q = q.where(Trade.future_code.in_(list(futures)))
        res = s.execute(q)
        return res.rowcount or 0
