from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException

from schemas.predict import PredictInput, PredictResponse, PredictResult
from services import predict_service

router = APIRouter(tags=["IA / Prédiction"])
logger = logging.getLogger(__name__)


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Prédiction de substitution avion→train",
    description=(
        "Prédit la classe de substitution modale pour une ou plusieurs liaisons ferroviaires. "
        "Retourne la classe prédite (`non_pertinent`, `substitution_difficile`, `substitution_possible`) "
        "ainsi que les probabilités associées à chaque classe. "
        "Le modèle utilisé est celui entraîné par M3 (MLP) ou M2 (classiques) si disponible."
    ),
)
async def post_predict(payload: list[PredictInput]) -> PredictResponse:
    if not payload:
        raise HTTPException(status_code=400, detail="Payload vide: fournir au moins une observation.")
    if len(payload) > 1000:
        raise HTTPException(status_code=400, detail="Taille du payload limitée à 1000 observations par requête.")

    t0 = time.perf_counter()
    try:
        data = [item.model_dump() for item in payload]
        raw = predict_service.predict(data)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Modèle non disponible: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Erreur inattendue lors de la prédiction: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la prédiction.") from exc

    latency_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "POST /predict | n=%d | latence=%.1fms | model=%s",
        len(payload),
        latency_ms,
        raw["model_name"],
    )

    results = [PredictResult(**item) for item in raw["results"]]
    return PredictResponse(
        results=results,
        model_name=raw["model_name"],
        count=raw["count"],
        model_source=raw.get("model_source"),
    )
