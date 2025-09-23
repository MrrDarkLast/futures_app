from datetime import date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Date, Numeric, Integer, ForeignKey, CheckConstraint, UniqueConstraint

class Base(DeclarativeBase): pass

class Future(Base):
    __tablename__ = "futures"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    expiration: Mapped["Expiration"] = relationship(back_populates="future", uselist=False, cascade="all, delete-orphan")
    trades: Mapped[list["Trade"]] = relationship(back_populates="future", cascade="all, delete-orphan")

class Expiration(Base):
    __tablename__ = "expirations"
    future_code: Mapped[str] = mapped_column(ForeignKey("futures.code", ondelete="CASCADE"), primary_key=True)
    expiry_date: Mapped["date"] = mapped_column(Date, nullable=False)

    future: Mapped[Future] = relationship(back_populates="expiration")

class Trade(Base):
    __tablename__ = "trades"
    trade_date: Mapped["date"] = mapped_column(Date, primary_key=True)
    future_code: Mapped[str] = mapped_column(ForeignKey("futures.code", ondelete="CASCADE"), primary_key=True)
    price_rub_per_usd: Mapped[float] = mapped_column(Numeric(18,6), nullable=False)
    contracts_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint("price_rub_per_usd > 0", name="ck_price_positive"),
        CheckConstraint("contracts_count IS NULL OR contracts_count >= 0", name="ck_contracts_nonneg"),
        UniqueConstraint("trade_date", "future_code", name="uq_trade"),
    )

    future: Mapped[Future] = relationship(back_populates="trades")
