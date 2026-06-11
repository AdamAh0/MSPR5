import os
import sys

import pytest
from httpx import ASGITransport, AsyncClient

from main import app, database

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
async def setup_db():
    """Connecte et déconnecte la base de données pour chaque test"""
    await database.connect()
    yield
    await database.disconnect()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
