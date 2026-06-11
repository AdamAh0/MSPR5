from __future__ import annotations

import logging
from math import ceil
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from database.connection import database
from utils.converters import normalize_type_train, to_float

router = APIRouter(tags=["Trajets"])
logger = logging.getLogger(__name__)


@router.get("/trajets")
async def get_trajets(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=100),
    id_operateur: Optional[str] = Query(None),
    id_ligne: Optional[str] = Query(None),
    id_gare_depart: Optional[str] = Query(None),
    id_gare_arrivee: Optional[str] = Query(None),
    code_pays_depart: Optional[str] = Query(None),
    code_pays_arrivee: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    co2_max: Optional[float] = Query(None, ge=0),
    duree_min: Optional[int] = Query(None, ge=0),
    duree_max: Optional[int] = Query(None, ge=0),
    search: Optional[str] = Query(None),
):
    type_normalized = normalize_type_train(type)
    offset = (page - 1) * limit

    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if id_operateur:
        conditions.append("t.id_operateur = :id_operateur")
        params["id_operateur"] = id_operateur
    if id_ligne:
        conditions.append("t.id_ligne = :id_ligne")
        params["id_ligne"] = id_ligne
    if id_gare_depart:
        conditions.append("t.id_gare_depart = :id_gare_depart")
        params["id_gare_depart"] = id_gare_depart
    if id_gare_arrivee:
        conditions.append("t.id_gare_arrivee = :id_gare_arrivee")
        params["id_gare_arrivee"] = id_gare_arrivee
    if code_pays_depart:
        conditions.append("gd.code_pays = :code_pays_depart")
        params["code_pays_depart"] = code_pays_depart.upper()
    if code_pays_arrivee:
        conditions.append("ga.code_pays = :code_pays_arrivee")
        params["code_pays_arrivee"] = code_pays_arrivee.upper()
    if co2_max is not None:
        conditions.append("t.emission_co2_kg <= :co2_max")
        params["co2_max"] = co2_max
    if duree_min is not None:
        conditions.append("t.duree_minutes >= :duree_min")
        params["duree_min"] = duree_min
    if duree_max is not None:
        conditions.append("t.duree_minutes <= :duree_max")
        params["duree_max"] = duree_max
    if type_normalized:
        conditions.append(
            "CASE WHEN t.heure_depart::time < TIME '18:00:00' THEN 'jour' ELSE 'nuit' END = :type_train"
        )
        params["type_train"] = type_normalized
    if search:
        conditions.append(
            "("
            "t.id_trajet ILIKE :search OR "
            "gd.nom_officiel ILIKE :search OR "
            "ga.nom_officiel ILIKE :search OR "
            "o.nom ILIKE :search"
            ")"
        )
        params["search"] = f"%{search}%"

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    count_params = {k: v for k, v in params.items() if k not in {"limit", "offset"}}

    count_query = f"""
        SELECT COUNT(*)
        FROM trajet t
        JOIN gare gd ON t.id_gare_depart = gd.id_gare
        JOIN gare ga ON t.id_gare_arrivee = ga.id_gare
        LEFT JOIN operateur o ON t.id_operateur = o.id_operateur
        {where}
    """

    data_query = f"""
        SELECT
            t.id_trajet,
            t.id_service,
            t.heure_depart,
            t.heure_arrivee,
            t.duree_minutes,
            t.emission_co2_kg,
            l.id_ligne,
            l.nom_ligne,
            o.id_operateur,
            o.nom AS operateur_nom,
            gd.id_gare AS depart_id_gare,
            gd.nom_officiel AS depart_nom,
            gd.ville AS depart_ville,
            gd.code_pays AS depart_code_pays,
            ga.id_gare AS arrivee_id_gare,
            ga.nom_officiel AS arrivee_nom,
            ga.ville AS arrivee_ville,
            ga.code_pays AS arrivee_code_pays
        FROM trajet t
        LEFT JOIN ligne l ON t.id_ligne = l.id_ligne
        LEFT JOIN operateur o ON t.id_operateur = o.id_operateur
        JOIN gare gd ON t.id_gare_depart = gd.id_gare
        JOIN gare ga ON t.id_gare_arrivee = ga.id_gare
        {where}
        ORDER BY t.id_trajet
        LIMIT :limit OFFSET :offset
    """

    try:
        total = await database.fetch_val(count_query, count_params)
        rows = await database.fetch_all(data_query, params)
    except Exception as exc:
        logger.error("Erreur GET /trajets : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur récupération trajets") from exc

    results = []
    for row in rows:
        type_calcul = "jour" if str(row["heure_depart"]) < "18:00:00" else "nuit"
        results.append(
            {
                "id_trajet": row["id_trajet"],
                "id_service": row["id_service"],
                "depart": {
                    "id_gare": row["depart_id_gare"],
                    "nom": row["depart_nom"],
                    "ville": row["depart_ville"],
                    "code_pays": row["depart_code_pays"],
                },
                "arrivee": {
                    "id_gare": row["arrivee_id_gare"],
                    "nom": row["arrivee_nom"],
                    "ville": row["arrivee_ville"],
                    "code_pays": row["arrivee_code_pays"],
                },
                "heure_depart": str(row["heure_depart"]),
                "heure_arrivee": str(row["heure_arrivee"]),
                "duree_minutes": row["duree_minutes"],
                "type_calcul": type_calcul,
                "emission_co2_kg": to_float(row["emission_co2_kg"]),
                "ligne": {"id_ligne": row["id_ligne"], "nom_ligne": row["nom_ligne"]},
                "operateur": {"id_operateur": row["id_operateur"], "nom": row["operateur_nom"]},
            }
        )

    total_int = int(total or 0)
    return {
        "page": page,
        "limit": limit,
        "total": total_int,
        "total_pages": ceil(total_int / limit) if total_int else 0,
        "results": results,
    }


@router.get("/trajets/{id_trajet}")
async def get_trajet(id_trajet: str):
    query = """
        SELECT
            t.id_trajet,
            t.id_service,
            t.id_trajet_source,
            t.heure_depart,
            t.heure_arrivee,
            t.duree_minutes,
            t.emission_co2_kg,
            l.id_ligne,
            l.nom_ligne,
            o.id_operateur,
            o.nom AS operateur_nom,
            gd.id_gare AS depart_id_gare,
            gd.nom_officiel AS depart_nom,
            gd.ville AS depart_ville,
            gd.code_pays AS depart_code_pays,
            ld.nom_pays AS depart_pays,
            gd.type_liaison AS depart_type_liaison,
            gd.latitude AS depart_lat,
            gd.longitude AS depart_lng,
            ga.id_gare AS arrivee_id_gare,
            ga.nom_officiel AS arrivee_nom,
            ga.ville AS arrivee_ville,
            ga.code_pays AS arrivee_code_pays,
            la.nom_pays AS arrivee_pays,
            ga.type_liaison AS arrivee_type_liaison,
            ga.latitude AS arrivee_lat,
            ga.longitude AS arrivee_lng
        FROM trajet t
        LEFT JOIN ligne l ON t.id_ligne = l.id_ligne
        LEFT JOIN operateur o ON t.id_operateur = o.id_operateur
        LEFT JOIN gare gd ON t.id_gare_depart = gd.id_gare
        LEFT JOIN gare ga ON t.id_gare_arrivee = ga.id_gare
        LEFT JOIN localisation ld ON gd.code_pays = ld.code_pays AND gd.ville = ld.ville
        LEFT JOIN localisation la ON ga.code_pays = la.code_pays AND ga.ville = la.ville
        WHERE t.id_trajet = :id_trajet
    """
    row = await database.fetch_one(query, {"id_trajet": id_trajet})
    if not row:
        raise HTTPException(status_code=404, detail=f"Trajet {id_trajet} non trouvé")

    type_calcul = "jour" if str(row["heure_depart"]) < "18:00:00" else "nuit"
    return {
        "id_trajet": row["id_trajet"],
        "id_service": row["id_service"],
        "id_trajet_source": row["id_trajet_source"],
        "depart": {
            "id_gare": row["depart_id_gare"],
            "nom_officiel": row["depart_nom"],
            "ville": row["depart_ville"],
            "code_pays": row["depart_code_pays"],
            "pays": row["depart_pays"],
            "type_liaison": row["depart_type_liaison"],
            "latitude": to_float(row["depart_lat"]),
            "longitude": to_float(row["depart_lng"]),
        },
        "arrivee": {
            "id_gare": row["arrivee_id_gare"],
            "nom_officiel": row["arrivee_nom"],
            "ville": row["arrivee_ville"],
            "code_pays": row["arrivee_code_pays"],
            "pays": row["arrivee_pays"],
            "type_liaison": row["arrivee_type_liaison"],
            "latitude": to_float(row["arrivee_lat"]),
            "longitude": to_float(row["arrivee_lng"]),
        },
        "heure_depart": str(row["heure_depart"]),
        "heure_arrivee": str(row["heure_arrivee"]),
        "duree_minutes": row["duree_minutes"],
        "type_calcul": type_calcul,
        "emission_co2_kg": to_float(row["emission_co2_kg"]),
        "ligne": {"id_ligne": row["id_ligne"], "nom_ligne": row["nom_ligne"]},
        "operateur": {"id_operateur": row["id_operateur"], "nom": row["operateur_nom"]},
    }
