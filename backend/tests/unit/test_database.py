"""Tests for database operations."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AnalysisResult


@pytest.mark.integration
class TestAnalysisResultORM:
    async def test_create_and_read(self, db_session: AsyncSession) -> None:
        record = AnalysisResult(
            symbol="EURUSD",
            timeframe="H1",
            status="completed",
            result_json='{"test": true}',
        )
        db_session.add(record)
        await db_session.commit()

        result = await db_session.execute(select(AnalysisResult).where(AnalysisResult.symbol == "EURUSD"))
        row = result.scalar_one()
        assert row.symbol == "EURUSD"
        assert row.timeframe == "H1"
        assert row.status == "completed"
        assert row.result_json == '{"test": true}'
        assert row.id is not None

    async def test_default_status(self, db_session: AsyncSession) -> None:
        record = AnalysisResult(symbol="GOLD", timeframe="D1")
        db_session.add(record)
        await db_session.commit()

        result = await db_session.execute(select(AnalysisResult).where(AnalysisResult.symbol == "GOLD"))
        row = result.scalar_one()
        assert row.status == "pending"

    async def test_update_result(self, db_session: AsyncSession) -> None:
        record = AnalysisResult(symbol="US500", timeframe="H4", status="running")
        db_session.add(record)
        await db_session.commit()

        record.status = "completed"
        record.result_json = '{"indicators": []}'
        await db_session.commit()

        result = await db_session.execute(select(AnalysisResult).where(AnalysisResult.symbol == "US500"))
        row = result.scalar_one()
        assert row.status == "completed"
        assert row.result_json == '{"indicators": []}'
