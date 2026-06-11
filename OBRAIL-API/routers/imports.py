from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from database.connection import database
from utils.converters import normalize_statut, to_iso

router = APIRouter(tags=["Imports"])
logger = logging.getLogger(__name__)


@router.get("/imports")
async def get_imports(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    statut: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
):
    statut_norm = normalize_statut(statut)
    offset = (page - 1) * limit

    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if statut_norm:
        conditions.append("LOWER(hi.statut) IN (:statut_1, :statut_2)")
        params["statut_1"] = statut_norm
        params["statut_2"] = "echec" if statut_norm == "échec" else statut_norm
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="since doit être une date ISO-8601") from exc
        if since_dt.tzinfo is not None:
            since_dt = since_dt.astimezone(timezone.utc).replace(tzinfo=None)
        conditions.append("hi.date_import >= :since")
        params["since"] = since_dt

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    count_params = {k: v for k, v in params.items() if k not in {"limit", "offset"}}

    total = await database.fetch_val(f"SELECT COUNT(*) FROM historique_import hi {where}", count_params)
    rows = await database.fetch_all(
        f"""
        SELECT hi.id_import, hi.date_import, hi.nb_lignes_importees, hi.statut, hi.message
        FROM historique_import hi
        {where}
        ORDER BY hi.date_import DESC
        LIMIT :limit OFFSET :offset
        """,
        params,
    )

    return {
        "page": page,
        "limit": limit,
        "total": int(total or 0),
        "imports": [
            {
                "id_import": int(row["id_import"]),
                "date_import": to_iso(row["date_import"]),
                "nb_lignes_importees": int(row["nb_lignes_importees"]),
                "statut": row["statut"],
                "message": row["message"],
            }
            for row in rows
        ],
    }


@router.get("/imports/stats")
async def get_imports_stats():
    row = await database.fetch_one(
        """
        SELECT
            COUNT(*) AS total_imports,
            COUNT(*) FILTER (WHERE LOWER(statut) = 'succès' OR LOWER(statut) = 'succes') AS imports_reussis,
            COUNT(*) FILTER (WHERE LOWER(statut) = 'échec' OR LOWER(statut) = 'echec') AS imports_echoues,
            COUNT(*) FILTER (WHERE LOWER(statut) = 'partiel') AS imports_partiels,
            COALESCE(SUM(nb_lignes_importees), 0) AS lignes_importees_total,
            MAX(date_import) AS dernier_import_date
        FROM historique_import
        """
    )

    last_row = await database.fetch_one(
        """
        SELECT date_import, statut, nb_lignes_importees
        FROM historique_import
        ORDER BY date_import DESC
        LIMIT 1
        """
    )

    total = int(row["total_imports"])
    ok = int(row["imports_reussis"])
    ko = int(row["imports_echoues"])
    partial = int(row["imports_partiels"])

    return {
        "total_imports": total,
        "imports_reussis": ok,
        "imports_echoues": ko,
        "imports_partiels": partial,
        "taux_reussite": round(ok / total, 3) if total else 0,
        "dernier_import": {
            "date_import": to_iso(last_row["date_import"]) if last_row else None,
            "statut": last_row["statut"] if last_row else None,
            "nb_lignes_importees": int(last_row["nb_lignes_importees"]) if last_row else 0,
        },
        "lignes_importees_total": int(row["lignes_importees_total"]),
    }
