from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "duree_minutes",
    "heure_decimale",
    "is_nuit",
    "is_transfrontalier",
    "code_pays_dep",
    "code_pays_arr",
]

logger = logging.getLogger(__name__)

_model_cache: dict[str, Any] = {}


def _find_model_path() -> Path:
    env_path = os.getenv("MODEL_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
        logger.warning("MODEL_PATH env var pointe vers un fichier inexistant: %s", env_path)

    candidates = [
        Path("artifacts/member3/best_model.joblib"),
        Path("../ia-mspr-/artifacts/member3/best_model.joblib"),
        Path("artifacts/member2/best_model.joblib"),
        Path("../ia-mspr-/artifacts/member2/best_model.joblib"),
    ]
    for candidate in candidates:
        if candidate.exists():
            logger.info("Modèle trouvé: %s", candidate)
            return candidate

    raise FileNotFoundError(
        "Aucun fichier modèle trouvé. "
        "Entraînez le modèle d'abord (member3_mlp.py ou member2_ml.py) "
        "ou définissez la variable d'environnement MODEL_PATH."
    )


def load_model(force_reload: bool = False) -> dict[str, Any]:
    if force_reload or "artifact" not in _model_cache:
        model_path = _find_model_path()
        artifact = joblib.load(model_path)
        if not isinstance(artifact, dict):
            raise ValueError("Format d'artefact modèle invalide: dict attendu.")
        required_keys = {"pipeline", "label_encoder", "class_names"}
        missing = required_keys.difference(artifact)
        if missing:
            raise ValueError(f"Artefact incomplet, clés manquantes: {sorted(missing)}")
        _model_cache["artifact"] = artifact
        _model_cache["path"] = str(model_path)
        logger.info("Modèle '%s' chargé depuis %s", artifact.get("model_name", "?"), model_path)
    return _model_cache["artifact"]


def get_model_source() -> str:
    return _model_cache.get("path", "non chargé")


def predict(payload: list[dict[str, Any]]) -> dict[str, Any]:
    artifact = load_model()
    pipeline = artifact["pipeline"]
    label_encoder = artifact["label_encoder"]
    class_names: list[str] = artifact["class_names"]

    frame = pd.DataFrame(payload)
    missing_cols = [c for c in FEATURE_COLUMNS if c not in frame.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans le payload: {missing_cols}")
    frame = frame[FEATURE_COLUMNS].copy()

    proba = pipeline.predict_proba(frame)
    pred_idx = np.argmax(proba, axis=1)
    predictions = label_encoder.inverse_transform(pred_idx)

    results = []
    for i, pred in enumerate(predictions):
        proba_dict = {cls: float(proba[i, j]) for j, cls in enumerate(class_names)}
        item: dict[str, Any] = {
            "prediction": str(pred),
            "probabilities": proba_dict,
        }
        for cls in class_names:
            safe_key = f"proba_{cls}"
            item[safe_key] = proba_dict[cls]
        # Ensure the three expected keys exist (fill with 0.0 if a class is absent)
        for default_cls in ["non_pertinent", "substitution_difficile", "substitution_possible"]:
            item.setdefault(f"proba_{default_cls}", 0.0)
        results.append(item)

    return {
        "results": results,
        "model_name": artifact.get("model_name", "unknown"),
        "count": len(results),
        "model_source": get_model_source(),
    }
