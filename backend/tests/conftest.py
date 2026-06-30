import math
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import create_access_token, require_auth
from app.core.database import Base, get_db
from app.core.models import OHLCVData
from app.main import app


@pytest.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession]:
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
def auth_token() -> str:
    return create_access_token(data={"sub": "dev"})


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    async def _override_require_auth():
        return "dev"

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[require_auth] = _override_require_auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(db_session: AsyncSession, auth_headers: dict[str, str]) -> AsyncGenerator[AsyncClient]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def raw_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sample_ohlcv_data() -> list[OHLCVData]:
    """Generate sample OHLCV data for testing (20 candles, uptrend)."""
    base_time = datetime(2024, 1, 1, tzinfo=UTC)
    data: list[OHLCVData] = []
    price = 100.0
    for i in range(20):
        o = price
        h = price + 2.0
        l = price - 1.0  # noqa: E741
        c = price + 1.5
        data.append(
            OHLCVData(
                timestamp=base_time.replace(hour=i % 24),
                open=round(o, 2),
                high=round(h, 2),
                low=round(l, 2),
                close=round(c, 2),
                volume=1000.0 + i * 100,
            )
        )
        price = c
    return data


@pytest.fixture
def sample_ohlcv_data_long() -> list[OHLCVData]:
    """Generate 250 OHLCV candles with mixed trends for indicator testing."""
    base_time = datetime(2024, 1, 1, tzinfo=UTC)
    data: list[OHLCVData] = []
    for i in range(250):
        trend = 100.0 + i * 0.04 + 10 * math.sin(i * 0.04)
        oscillation = 2 * math.sin(i * 0.5)
        c = round(trend + oscillation, 2)
        o = round(trend + oscillation * 0.7, 2)
        h = round(max(o, c) + abs(oscillation * 0.3) + 0.5, 2)
        low = round(min(o, c) - abs(oscillation * 0.3) - 0.5, 2)
        v = round(1000.0 + 500 * abs(math.sin(i * 0.2)), 2)
        data.append(
            OHLCVData(
                timestamp=base_time + timedelta(hours=i),
                open=o,
                high=h,
                low=low,
                close=c,
                volume=v,
            )
        )
    return data
