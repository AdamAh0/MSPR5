from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PredictInput(BaseModel):
    duree_minutes: float = Field(..., description="Durée du trajet en minutes", ge=0)
    heure_decimale: float = Field(..., description="Heure de départ en décimal (ex: 8.5 = 08h30)", ge=0, lt=24)
    is_nuit: int = Field(..., description="1 si trajet de nuit, 0 sinon", ge=0, le=1)
    is_transfrontalier: int = Field(..., description="1 si trajet transfrontalier, 0 sinon", ge=0, le=1)
    code_pays_dep: str = Field(..., description="Code ISO du pays de départ (ex: FR, DE)", min_length=2, max_length=2)
    code_pays_arr: str = Field(..., description="Code ISO du pays d'arrivée (ex: FR, DE)", min_length=2, max_length=2)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "duree_minutes": 120.0,
                    "heure_decimale": 8.5,
                    "is_nuit": 0,
                    "is_transfrontalier": 0,
                    "code_pays_dep": "FR",
                    "code_pays_arr": "FR",
                }
            ]
        }
    }


class PredictResult(BaseModel):
    prediction: str = Field(..., description="Classe prédite")
    proba_non_pertinent: Optional[float] = Field(None, description="Probabilité classe non_pertinent")
    proba_substitution_difficile: Optional[float] = Field(None, description="Probabilité classe substitution_difficile")
    proba_substitution_possible: Optional[float] = Field(None, description="Probabilité classe substitution_possible")
    probabilities: dict[str, float] = Field(default_factory=dict, description="Probabilités par classe")


class PredictResponse(BaseModel):
    results: list[PredictResult]
    model_name: str = Field(..., description="Nom du modèle utilisé pour la prédiction")
    count: int = Field(..., description="Nombre d'observations prédites")
    model_source: Optional[str] = Field(None, description="Chemin du fichier modèle chargé")
