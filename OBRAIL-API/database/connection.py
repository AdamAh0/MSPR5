from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import databases
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
database = databases.Database(DATABASE_URL)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await database.connect()
        logger.info("PostgreSQL connection established")
    except Exception as exc:
        logger.warning(
            "PostgreSQL non disponible au démarrage (%s). "
            "Les routes DB retourneront 503. La route /predict reste fonctionnelle.",
            exc,
        )
    yield
    try:
        await database.disconnect()
        logger.info("PostgreSQL connection closed")
    except Exception:
        pass
