from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Query

from database.connection import database
from utils.converters import parse_bbox, to_float

router = APIRouter(tags=["Référentiels"])
logger = logging.getLogger(__name__)


@router.get("/operateurs")
async def get_operateurs():
    rows = await database.fetch_all(
        """
        SELECT
            o.id_operateur,
            o.nom,
            COUNT(t.id_trajet) AS nb_trajets,
            COUNT(DISTINCT t.id_ligne) AS nb_lignes
        FROM operateur o
        LEFT JOIN trajet t ON t.id_operateur = o.id_operateur
        GROUP BY o.id_operateur, o.nom
        ORDER BY nb_trajets DESC
        """
    )
    return {
        "operateurs": [
            {
                "id_operateur": row["id_operateur"],
                "nom": row["nom"],
                "nb_trajets": int(row["nb_trajets"]),
                "nb_lignes": int(row["nb_lignes"]),
            }
            for row in rows
        ]
    }


@router.get("/lignes")
async def get_lignes(
    id_operateur: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    conditions: list[str] = []
    params: dict[str, Any] = {}

    if id_operateur:
        conditions.append("t.id_operateur = :id_operateur")
        params["id_operateur"] = id_operateur
    if search:
        conditions.append("(l.id_ligne ILIKE :search OR l.nom_ligne ILIKE :search)")
        params["search"] = f"%{search}%"

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    lines = await database.fetch_all(
        f"""
        SELECT
            l.id_ligne,
            l.nom_ligne,
            COUNT(t.id_trajet) AS nb_trajets,
            COALESCE(AVG(t.emission_co2_kg), 0) AS co2_moyen_kg,
            COALESCE(AVG(t.duree_minutes), 0) AS duree_moyenne_minutes
        FROM ligne l
        LEFT JOIN trajet t ON t.id_ligne = l.id_ligne
        {where}
        GROUP BY l.id_ligne, l.nom_ligne
        ORDER BY nb_trajets DESC, l.nom_ligne
        """,
        params,
    )

    operator_rows = await database.fetch_all(
        f"""
        SELECT DISTINCT t.id_ligne, o.id_operateur, o.nom
        FROM trajet t
        JOIN operateur o ON o.id_operateur = t.id_operateur
        LEFT JOIN ligne l ON l.id_ligne = t.id_ligne
        {where}
        """,
        params,
    )

    by_line: dict[str, list[dict[str, Any]]] = {}
    for row in operator_rows:
        by_line.setdefault(row["id_ligne"], []).append({"id_operateur": row["id_operateur"], "nom": row["nom"]})

    return {
        "lignes": [
            {
                "id_ligne": row["id_ligne"],
                "nom_ligne": row["nom_ligne"],
                "nb_trajets": int(row["nb_trajets"]),
                "operateurs": by_line.get(row["id_ligne"], []),
                "co2_moyen_kg": to_float(row["co2_moyen_kg"]),
                "duree_moyenne_minutes": round(to_float(row["duree_moyenne_minutes"]) or 0),
            }
            for row in lines
        ]
    }


@router.get("/gares")
async def get_gares(
    code_pays: Optional[str] = Query(None),
    type_liaison: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    bbox: Optional[str] = Query(None),
):
    bbox_values = parse_bbox(bbox)

    conditions: list[str] = []
    params: dict[str, Any] = {}

    if code_pays:
        conditions.append("g.code_pays = :code_pays")
        params["code_pays"] = code_pays.upper()
    if type_liaison:
        conditions.append("g.type_liaison = :type_liaison")
        params["type_liaison"] = type_liaison
    if search:
        conditions.append("(g.id_gare ILIKE :search OR g.nom_officiel ILIKE :search OR g.ville ILIKE :search)")
        params["search"] = f"%{search}%"
    if bbox_values:
        lat_min, lng_min, lat_max, lng_max = bbox_values
        conditions.append("g.latitude BETWEEN :lat_min AND :lat_max")
        conditions.append("g.longitude BETWEEN :lng_min AND :lng_max")
        params.update({"lat_min": lat_min, "lat_max": lat_max, "lng_min": lng_min, "lng_max": lng_max})

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    rows = await database.fetch_all(
        f"""
        SELECT
            g.id_gare,
            g.nom_officiel,
            g.ville,
            g.code_pays,
            l.nom_pays AS pays,
            g.type_liaison,
            g.latitude,
            g.longitude,
            COUNT(t1.id_trajet) AS nb_departs,
            COUNT(t2.id_trajet) AS nb_arrivees
        FROM gare g
        LEFT JOIN localisation l ON l.code_pays = g.code_pays AND l.ville = g.ville
        LEFT JOIN trajet t1 ON t1.id_gare_depart = g.id_gare
        LEFT JOIN trajet t2 ON t2.id_gare_arrivee = g.id_gare
        {where}
        GROUP BY g.id_gare, g.nom_officiel, g.ville, g.code_pays, l.nom_pays, g.type_liaison, g.latitude, g.longitude
        ORDER BY g.code_pays, g.ville, g.nom_officiel
        """,
        params,
    )

    return {
        "gares": [
            {
                "id_gare": row["id_gare"],
                "nom_officiel": row["nom_officiel"],
                "ville": row["ville"],
                "code_pays": row["code_pays"],
                "pays": row["pays"],
                "type_liaison": row["type_liaison"],
                "latitude": to_float(row["latitude"]),
                "longitude": to_float(row["longitude"]),
                "nb_departs": int(row["nb_departs"]),
                "nb_arrivees": int(row["nb_arrivees"]),
            }
            for row in rows
        ]
    }


@router.get("/pays")
async def get_pays():
    rows = await database.fetch_all(
        """
        SELECT
            g.code_pays,
            MAX(l.nom_pays) AS nom_pays,
            COUNT(DISTINCT g.id_gare) AS nb_gares,
            COUNT(t.id_trajet) AS nb_trajets_depart
        FROM gare g
        LEFT JOIN localisation l ON l.code_pays = g.code_pays
        LEFT JOIN trajet t ON t.id_gare_depart = g.id_gare
        GROUP BY g.code_pays
        ORDER BY g.code_pays
        """
    )
    return {
        "pays": [
            {
                "code_pays": row["code_pays"],
                "nom_pays": row["nom_pays"],
                "nb_gares": int(row["nb_gares"]),
                "nb_trajets_depart": int(row["nb_trajets_depart"]),
            }
            for row in rows
        ]
    }
