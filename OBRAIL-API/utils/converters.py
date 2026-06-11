from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


def normalize_type_train(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.lower().strip()
    if v not in {"jour", "nuit"}:
        raise HTTPException(status_code=400, detail="type doit être 'jour' ou 'nuit'")
    return v


def parse_bbox(value: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    if value is None:
        return None
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox doit être 'lat_min,lng_min,lat_max,lng_max'")
    try:
        lat_min, lng_min, lat_max, lng_max = [float(p) for p in parts]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bbox invalide") from exc
    if lat_min > lat_max or lng_min > lng_max:
        raise HTTPException(status_code=400, detail="bbox invalide: min > max")
    return lat_min, lng_min, lat_max, lng_max


def normalize_statut(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = value.strip().lower()
    mapping = {
        "succes": "succès",
        "succès": "succès",
        "echec": "échec",
        "échec": "échec",
        "partiel": "partiel",
    }
    if raw not in mapping:
        raise HTTPException(status_code=400, detail="statut invalide : succès | échec | partiel")
    return mapping[raw]


def normalize_groupby(value: str) -> str:
    valid = {"operateur", "ligne", "pays_depart", "pays_arrivee", "jour_nuit"}
    if value not in valid:
        raise HTTPException(status_code=400, detail="groupby invalide")
    return value
