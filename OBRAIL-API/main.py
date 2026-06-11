from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database.connection import database, lifespan  # `database` re-exported for tests/conftest.py
from routers import compat, imports, predict, referentiels, stats, trajets

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ObRail Europe API",
    description="API REST adaptée à la base ObRail Europe",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"code": 404, "message": "Ressource non trouvée", "detail": getattr(exc, "detail", str(exc))},
    )


@app.exception_handler(422)
async def validation_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "Paramètre invalide", "detail": "Vérifiez les paramètres"},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error("500 - %s - %s", request.url, exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "Erreur serveur interne", "detail": "Une erreur inattendue s'est produite"},
    )


@app.get("/", tags=["Racine"])
async def root():
    return {
        "api": "ObRail Europe",
        "version": "3.0.0",
        "documentation": "/docs",
        "endpoints": [
            "/trajets",
            "/trajets/{id_trajet}",
            "/stats/kpi",
            "/stats/volumes",
            "/stats/comparatif-jour-nuit",
            "/stats/co2",
            "/stats/top-liaisons",
            "/operateurs",
            "/lignes",
            "/gares",
            "/pays",
            "/imports",
            "/imports/stats",
            "/predict",
            "/health",
        ],
    }


@app.get("/health", tags=["System"])
async def health():
    from database.connection import database
    from datetime import datetime, timezone

    db_status = "ok"
    try:
        await database.fetch_val("SELECT 1")
    except Exception:
        db_status = "error"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": "3.0.0",
        "components": {"db": db_status},
    }


app.include_router(trajets.router)
app.include_router(stats.router)
app.include_router(referentiels.router)
app.include_router(imports.router)
app.include_router(predict.router)
app.include_router(compat.router)
