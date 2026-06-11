"""
Tests unitaires pour la route POST /predict (Membre 3).

Les tests utilisent des mocks pour le predict_service afin de ne pas
dépendre de la présence du fichier modèle .joblib.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

from main import app


VALID_PAYLOAD = [
    {
        "duree_minutes": 120.0,
        "heure_decimale": 8.5,
        "is_nuit": 0,
        "is_transfrontalier": 0,
        "code_pays_dep": "FR",
        "code_pays_arr": "FR",
    }
]

VALID_PAYLOAD_CROSS_BORDER = [
    {
        "duree_minutes": 400.0,
        "heure_decimale": 22.0,
        "is_nuit": 1,
        "is_transfrontalier": 1,
        "code_pays_dep": "FR",
        "code_pays_arr": "DE",
    },
    {
        "duree_minutes": 90.0,
        "heure_decimale": 10.0,
        "is_nuit": 0,
        "is_transfrontalier": 0,
        "code_pays_dep": "DE",
        "code_pays_arr": "DE",
    },
]

MOCK_PREDICT_RESULT = {
    "results": [
        {
            "prediction": "substitution_possible",
            "probabilities": {
                "non_pertinent": 0.1,
                "substitution_difficile": 0.2,
                "substitution_possible": 0.7,
            },
            "proba_non_pertinent": 0.1,
            "proba_substitution_difficile": 0.2,
            "proba_substitution_possible": 0.7,
        }
    ],
    "model_name": "mlp",
    "count": 1,
    "model_source": "artifacts/member3/best_model.joblib",
}

MOCK_PREDICT_RESULT_2 = {
    "results": [
        {
            "prediction": "substitution_possible",
            "probabilities": {"non_pertinent": 0.05, "substitution_difficile": 0.15, "substitution_possible": 0.80},
            "proba_non_pertinent": 0.05,
            "proba_substitution_difficile": 0.15,
            "proba_substitution_possible": 0.80,
        },
        {
            "prediction": "non_pertinent",
            "probabilities": {"non_pertinent": 0.70, "substitution_difficile": 0.20, "substitution_possible": 0.10},
            "proba_non_pertinent": 0.70,
            "proba_substitution_difficile": 0.20,
            "proba_substitution_possible": 0.10,
        },
    ],
    "model_name": "mlp",
    "count": 2,
    "model_source": "artifacts/member3/best_model.joblib",
}


class TestPredict:

    @pytest.mark.asyncio
    async def test_predict_returns_200(self, client: AsyncClient):
        with patch("services.predict_service.predict", return_value=MOCK_PREDICT_RESULT):
            response = await client.post("/predict", json=VALID_PAYLOAD)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_predict_response_structure(self, client: AsyncClient):
        with patch("services.predict_service.predict", return_value=MOCK_PREDICT_RESULT):
            response = await client.post("/predict", json=VALID_PAYLOAD)
        data = response.json()
        assert "results" in data
        assert "model_name" in data
        assert "count" in data
        assert data["count"] == 1
        assert len(data["results"]) == 1

    @pytest.mark.asyncio
    async def test_predict_result_has_prediction_and_probas(self, client: AsyncClient):
        with patch("services.predict_service.predict", return_value=MOCK_PREDICT_RESULT):
            response = await client.post("/predict", json=VALID_PAYLOAD)
        result = response.json()["results"][0]
        assert "prediction" in result
        assert result["prediction"] in {"non_pertinent", "substitution_difficile", "substitution_possible"}
        assert "proba_non_pertinent" in result
        assert "proba_substitution_difficile" in result
        assert "proba_substitution_possible" in result

    @pytest.mark.asyncio
    async def test_predict_multiple_observations(self, client: AsyncClient):
        with patch("services.predict_service.predict", return_value=MOCK_PREDICT_RESULT_2):
            response = await client.post("/predict", json=VALID_PAYLOAD_CROSS_BORDER)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["results"]) == 2

    @pytest.mark.asyncio
    async def test_predict_empty_payload_returns_400(self, client: AsyncClient):
        response = await client.post("/predict", json=[])
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_predict_missing_field_returns_422(self, client: AsyncClient):
        incomplete = [{"duree_minutes": 120.0, "heure_decimale": 8.5}]
        response = await client.post("/predict", json=incomplete)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_model_not_found_returns_503(self, client: AsyncClient):
        with patch(
            "services.predict_service.predict",
            side_effect=FileNotFoundError("Aucun fichier modèle trouvé"),
        ):
            response = await client.post("/predict", json=VALID_PAYLOAD)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_predict_invalid_country_code_returns_422(self, client: AsyncClient):
        bad_payload = [
            {
                "duree_minutes": 120.0,
                "heure_decimale": 8.5,
                "is_nuit": 0,
                "is_transfrontalier": 0,
                "code_pays_dep": "FRA",
                "code_pays_arr": "FR",
            }
        ]
        response = await client.post("/predict", json=bad_payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_negative_duration_returns_422(self, client: AsyncClient):
        bad_payload = [
            {
                "duree_minutes": -10.0,
                "heure_decimale": 8.5,
                "is_nuit": 0,
                "is_transfrontalier": 0,
                "code_pays_dep": "FR",
                "code_pays_arr": "FR",
            }
        ]
        response = await client.post("/predict", json=bad_payload)
        assert response.status_code == 422
