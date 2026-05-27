"""SQLAlchemy async storage — works with SQLite (MVP) or Postgres (Railway free tier)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    DateTime, Float, Integer, String, Text, select, and_, desc,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.utils.logging import get_logger

log = get_logger(__name__)


class Base(DeclarativeBase):
    pass


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    interval: Mapped[str] = mapped_column(String(8), nullable=False)
    agreeing: Mapped[int] = mapped_column(Integer, nullable=False)
    total_active: Mapped[int] = mapped_column(Integer, nullable=False)
    components_json: Mapped[str] = mapped_column(Text, nullable=False)
    narration: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "action": self.action,
            "score": self.score,
            "interval": self.interval,
            "agreeing": self.agreeing,
            "total_active": self.total_active,
            "components": json.loads(self.components_json),
            "narration": self.narration,
            "created_at": self.created_at.isoformat(),
        }


class SignalStore:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def init(self) -> None:
        if self.database_url.startswith("sqlite"):
            # ensure data dir exists for file-based sqlite
            path_part = self.database_url.split("///", 1)[-1].lstrip("/")
            db_path = Path(path_part)
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self._engine = create_async_engine(self.database_url, future=True)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("storage initialised: %s", self.database_url)

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()

    def _session(self) -> AsyncSession:
        if not self._session_factory:
            raise RuntimeError("SignalStore not initialised — call init() first")
        return self._session_factory()

    async def save_signal(self, payload: dict[str, Any]) -> int:
        async with self._session() as s:
            row = Signal(
                symbol=payload["symbol"],
                action=payload["action"],
                score=float(payload["score"]),
                interval=payload["interval"],
                agreeing=int(payload["agreeing"]),
                total_active=int(payload["total_active"]),
                components_json=json.dumps(payload["components"], ensure_ascii=False),
                narration=payload.get("narration"),
            )
            s.add(row)
            await s.commit()
            await s.refresh(row)
            return row.id

    async def has_recent_signal(self, symbol: str, action: str, cooldown_minutes: int) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)
        async with self._session() as s:
            stmt = select(Signal.id).where(
                and_(
                    Signal.symbol == symbol,
                    Signal.action == action,
                    Signal.created_at >= cutoff,
                )
            ).limit(1)
            result = await s.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def recent_signals(
        self, limit: int = 50, symbol: str | None = None
    ) -> list[dict[str, Any]]:
        async with self._session() as s:
            stmt = select(Signal).order_by(desc(Signal.created_at)).limit(limit)
            if symbol:
                stmt = stmt.where(Signal.symbol == symbol.upper())
            result = await s.execute(stmt)
            return [row.to_dict() for row in result.scalars()]
