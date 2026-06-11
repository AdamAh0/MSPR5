from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query

from database.connection import database
from utils.converters import to_float
from routers.stats import get_stats_kpi, get_stats_volumes

router = APIRouter(tags=["Compat"])


@router.get("/dashboard")
async def get_dashboard():
    return await get_stats_kpi()


@router.get("/emissions/stats")
async def get_emissions_stats_compat():
    payload = await get_stats_volumes(groupby="operateur")
    return [
        {
            "operateur": item["nom"],
            "nb_trajets": item["trajets"],
            "emission_moyenne_kg": None,
        }
        for item in payload["repartition"]
    ]


@router.get("/localisations")
async def get_localisations_compat(code_pays: Optional[str] = Query(None, min_length=2, max_length=2)):
    params: dict[str, Any] = {}
    where = ""
    if code_pays:
        where = "WHERE code_pays = :code_pays"
        params["code_pays"] = code_pays.upper()
    rows = await database.fetch_all(
        f"SELECT DISTINCT code_pays, nom_pays, ville FROM localisation {where} ORDER BY code_pays, ville",
        params,
    )
    return [dict(r) for r in rows]
