from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from database.connection import database
from utils.converters import normalize_groupby, to_float

router = APIRouter(tags=["Stats"])
logger = logging.getLogger(__name__)


@router.get("/stats/kpi")
async def get_stats_kpi():
    query = """
        SELECT
            (SELECT COUNT(*) FROM trajet) AS total_trajets,
            (SELECT COUNT(*) FROM trajet WHERE heure_depart::time < TIME '18:00:00') AS trajets_jour,
            (SELECT COUNT(*) FROM trajet WHERE heure_depart::time >= TIME '18:00:00') AS trajets_nuit,
            (SELECT COUNT(*) FROM operateur) AS total_operateurs,
            (SELECT COUNT(*) FROM ligne) AS total_lignes,
            (SELECT COUNT(*) FROM gare) AS total_gares,
            (SELECT COUNT(DISTINCT code_pays) FROM gare) AS total_pays,
            (SELECT COALESCE(SUM(emission_co2_kg), 0) FROM trajet) AS co2_total_kg,
            (SELECT COALESCE(AVG(emission_co2_kg), 0) FROM trajet) AS co2_moyen_kg,
            (SELECT COALESCE(AVG(duree_minutes), 0) FROM trajet) AS duree_moyenne_minutes
    """
    row = await database.fetch_one(query)
    return {
        "total_trajets": int(row["total_trajets"]),
        "trajets_jour": int(row["trajets_jour"]),
        "trajets_nuit": int(row["trajets_nuit"]),
        "total_operateurs": int(row["total_operateurs"]),
        "total_lignes": int(row["total_lignes"]),
        "total_gares": int(row["total_gares"]),
        "total_pays": int(row["total_pays"]),
        "co2_total_kg": to_float(row["co2_total_kg"]),
        "co2_moyen_kg": to_float(row["co2_moyen_kg"]),
        "duree_moyenne_minutes": round(to_float(row["duree_moyenne_minutes"]) or 0),
    }


@router.get("/stats/volumes")
async def get_stats_volumes(groupby: str = Query("operateur")):
    groupby = normalize_groupby(groupby)

    if groupby == "operateur":
        rows = await database.fetch_all(
            """
            SELECT o.id_operateur, o.nom,
                   COUNT(t.id_trajet) AS trajets,
                   COALESCE(SUM(t.emission_co2_kg), 0) AS co2_total_kg
            FROM trajet t
            JOIN operateur o ON t.id_operateur = o.id_operateur
            GROUP BY o.id_operateur, o.nom
            ORDER BY trajets DESC
            """
        )
        total = sum(int(r["trajets"]) for r in rows)
        return {
            "groupby": groupby,
            "total": total,
            "repartition": [
                {
                    "id_operateur": r["id_operateur"],
                    "nom": r["nom"],
                    "trajets": int(r["trajets"]),
                    "co2_total_kg": to_float(r["co2_total_kg"]),
                    "part": round(int(r["trajets"]) / total, 3) if total else 0,
                }
                for r in rows
            ],
        }

    if groupby == "ligne":
        rows = await database.fetch_all(
            """
            SELECT l.id_ligne, l.nom_ligne,
                   COUNT(t.id_trajet) AS trajets,
                   COALESCE(SUM(t.emission_co2_kg), 0) AS co2_total_kg
            FROM trajet t
            JOIN ligne l ON t.id_ligne = l.id_ligne
            GROUP BY l.id_ligne, l.nom_ligne
            ORDER BY trajets DESC
            """
        )
        total = sum(int(r["trajets"]) for r in rows)
        return {
            "groupby": groupby,
            "total": total,
            "repartition": [
                {
                    "id_ligne": r["id_ligne"],
                    "nom_ligne": r["nom_ligne"],
                    "trajets": int(r["trajets"]),
                    "co2_total_kg": to_float(r["co2_total_kg"]),
                    "part": round(int(r["trajets"]) / total, 3) if total else 0,
                }
                for r in rows
            ],
        }

    if groupby == "pays_depart":
        rows = await database.fetch_all(
            """
            SELECT gd.code_pays,
                   COUNT(t.id_trajet) AS trajets,
                   COALESCE(SUM(t.emission_co2_kg), 0) AS co2_total_kg
            FROM trajet t
            JOIN gare gd ON t.id_gare_depart = gd.id_gare
            GROUP BY gd.code_pays
            ORDER BY trajets DESC
            """
        )
        total = sum(int(r["trajets"]) for r in rows)
        return {
            "groupby": groupby,
            "total": total,
            "repartition": [
                {
                    "code_pays": r["code_pays"],
                    "trajets": int(r["trajets"]),
                    "co2_total_kg": to_float(r["co2_total_kg"]),
                    "part": round(int(r["trajets"]) / total, 3) if total else 0,
                }
                for r in rows
            ],
        }

    if groupby == "pays_arrivee":
        rows = await database.fetch_all(
            """
            SELECT ga.code_pays,
                   COUNT(t.id_trajet) AS trajets,
                   COALESCE(SUM(t.emission_co2_kg), 0) AS co2_total_kg
            FROM trajet t
            JOIN gare ga ON t.id_gare_arrivee = ga.id_gare
            GROUP BY ga.code_pays
            ORDER BY trajets DESC
            """
        )
        total = sum(int(r["trajets"]) for r in rows)
        return {
            "groupby": groupby,
            "total": total,
            "repartition": [
                {
                    "code_pays": r["code_pays"],
                    "trajets": int(r["trajets"]),
                    "co2_total_kg": to_float(r["co2_total_kg"]),
                    "part": round(int(r["trajets"]) / total, 3) if total else 0,
                }
                for r in rows
            ],
        }

    # jour_nuit
    rows = await database.fetch_all(
        """
        SELECT CASE WHEN heure_depart::time < TIME '18:00:00' THEN 'jour' ELSE 'nuit' END AS type,
               COUNT(*) AS trajets,
               COALESCE(AVG(duree_minutes), 0) AS duree_moyenne_minutes,
               COALESCE(AVG(emission_co2_kg), 0) AS co2_moyen_kg
        FROM trajet
        GROUP BY type
        ORDER BY type
        """
    )
    total = sum(int(r["trajets"]) for r in rows)
    return {
        "groupby": "jour_nuit",
        "total": total,
        "repartition": [
            {
                "type": r["type"],
                "trajets": int(r["trajets"]),
                "duree_moyenne_minutes": round(to_float(r["duree_moyenne_minutes"]) or 0),
                "co2_moyen_kg": round(to_float(r["co2_moyen_kg"]) or 0, 2),
                "part": round(int(r["trajets"]) / total, 3) if total else 0,
            }
            for r in rows
        ],
    }


@router.get("/stats/comparatif-jour-nuit")
async def get_stats_comparatif_jour_nuit():
    row = await database.fetch_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE heure_depart::time < TIME '18:00:00') AS nb_jour,
            COUNT(*) FILTER (WHERE heure_depart::time >= TIME '18:00:00') AS nb_nuit,
            COALESCE(AVG(duree_minutes) FILTER (WHERE heure_depart::time < TIME '18:00:00'), 0) AS duree_jour,
            COALESCE(AVG(duree_minutes) FILTER (WHERE heure_depart::time >= TIME '18:00:00'), 0) AS duree_nuit,
            COALESCE(AVG(emission_co2_kg) FILTER (WHERE heure_depart::time < TIME '18:00:00'), 0) AS co2_moy_jour,
            COALESCE(AVG(emission_co2_kg) FILTER (WHERE heure_depart::time >= TIME '18:00:00'), 0) AS co2_moy_nuit,
            COALESCE(SUM(emission_co2_kg) FILTER (WHERE heure_depart::time < TIME '18:00:00'), 0) AS co2_total_jour,
            COALESCE(SUM(emission_co2_kg) FILTER (WHERE heure_depart::time >= TIME '18:00:00'), 0) AS co2_total_nuit
        FROM trajet
        """
    )
    return {
        "indicateurs": [
            {"label": "Nombre de trajets", "jour": int(row["nb_jour"]), "nuit": int(row["nb_nuit"]), "unite": ""},
            {
                "label": "Durée moyenne",
                "jour": round(to_float(row["duree_jour"]) or 0),
                "nuit": round(to_float(row["duree_nuit"]) or 0),
                "unite": "min",
            },
            {
                "label": "Émission CO₂ moyenne",
                "jour": round(to_float(row["co2_moy_jour"]) or 0, 2),
                "nuit": round(to_float(row["co2_moy_nuit"]) or 0, 2),
                "unite": "kg",
            },
            {
                "label": "Émission CO₂ totale",
                "jour": round(to_float(row["co2_total_jour"]) or 0, 2),
                "nuit": round(to_float(row["co2_total_nuit"]) or 0, 2),
                "unite": "kg",
            },
        ]
    }


@router.get("/stats/co2")
async def get_stats_co2():
    global_row = await database.fetch_one(
        """
        SELECT
            COALESCE(SUM(emission_co2_kg), 0) AS co2_total_kg,
            COALESCE(AVG(emission_co2_kg), 0) AS co2_moyen_kg_par_trajet
        FROM trajet
        """
    )
    operateurs = await database.fetch_all(
        """
        SELECT o.id_operateur, o.nom,
               COALESCE(SUM(t.emission_co2_kg), 0) AS co2_total_kg,
               COALESCE(AVG(t.emission_co2_kg), 0) AS co2_moyen_kg
        FROM trajet t
        JOIN operateur o ON t.id_operateur = o.id_operateur
        GROUP BY o.id_operateur, o.nom
        ORDER BY co2_total_kg DESC
        """
    )
    lignes_top = await database.fetch_all(
        """
        SELECT l.id_ligne, l.nom_ligne,
               COALESCE(SUM(t.emission_co2_kg), 0) AS co2_total_kg,
               COUNT(*) AS trajets
        FROM trajet t
        JOIN ligne l ON t.id_ligne = l.id_ligne
        GROUP BY l.id_ligne, l.nom_ligne
        ORDER BY co2_total_kg DESC
        LIMIT 10
        """
    )
    return {
        "co2_total_kg": to_float(global_row["co2_total_kg"]),
        "co2_moyen_kg_par_trajet": to_float(global_row["co2_moyen_kg_par_trajet"]),
        "par_operateur": [
            {
                "id_operateur": row["id_operateur"],
                "nom": row["nom"],
                "co2_total_kg": to_float(row["co2_total_kg"]),
                "co2_moyen_kg": to_float(row["co2_moyen_kg"]),
            }
            for row in operateurs
        ],
        "par_ligne_top10": [
            {
                "id_ligne": row["id_ligne"],
                "nom_ligne": row["nom_ligne"],
                "co2_total_kg": to_float(row["co2_total_kg"]),
                "trajets": int(row["trajets"]),
            }
            for row in lignes_top
        ],
    }


@router.get("/stats/top-liaisons")
async def get_stats_top_liaisons(limit: int = Query(10, ge=1, le=100)):
    rows = await database.fetch_all(
        """
        SELECT
            gd.id_gare AS depart_id_gare,
            gd.nom_officiel AS depart_nom,
            gd.ville AS depart_ville,
            gd.code_pays AS depart_code_pays,
            ga.id_gare AS arrivee_id_gare,
            ga.nom_officiel AS arrivee_nom,
            ga.ville AS arrivee_ville,
            ga.code_pays AS arrivee_code_pays,
            o.nom AS operateur,
            COUNT(*) AS trajets,
            COALESCE(AVG(t.duree_minutes), 0) AS duree_moyenne_minutes,
            CASE
                WHEN COUNT(*) FILTER (WHERE t.heure_depart::time < TIME '18:00:00') >=
                     COUNT(*) FILTER (WHERE t.heure_depart::time >= TIME '18:00:00')
                THEN 'jour'
                ELSE 'nuit'
            END AS type_dominant
        FROM trajet t
        JOIN gare gd ON t.id_gare_depart = gd.id_gare
        JOIN gare ga ON t.id_gare_arrivee = ga.id_gare
        LEFT JOIN operateur o ON t.id_operateur = o.id_operateur
        GROUP BY
            gd.id_gare, gd.nom_officiel, gd.ville, gd.code_pays,
            ga.id_gare, ga.nom_officiel, ga.ville, ga.code_pays,
            o.nom
        ORDER BY trajets DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {
        "results": [
            {
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
                "operateur": row["operateur"],
                "trajets": int(row["trajets"]),
                "duree_moyenne_minutes": round(to_float(row["duree_moyenne_minutes"]) or 0),
                "type_dominant": row["type_dominant"],
            }
            for row in rows
        ]
    }
