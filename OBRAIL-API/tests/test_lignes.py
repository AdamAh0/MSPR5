"""
Tests: Lignes
GET /lignes
"""

import pytest


class TestLignes:

    @pytest.mark.asyncio
    async def test_lignes_status_200(self, client):
        response = await client.get("/lignes")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_lignes_retourne_conteneur(self, client):
        response = await client.get("/lignes")
        data = response.json()
        assert isinstance(data, dict)
        assert "lignes" in data
        assert isinstance(data["lignes"], list)

    @pytest.mark.asyncio
    async def test_lignes_pagination_like_filter(self, client):
        response = await client.get("/lignes?search=Paris")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_lignes_champs_requis(self, client):
        response = await client.get("/lignes")
        data = response.json()
        if data["lignes"]:
            ligne = data["lignes"][0]
            assert "id_ligne"              in ligne
            assert "nom_ligne"             in ligne
            assert "nb_trajets"            in ligne
            assert "operateurs"            in ligne
            assert "co2_moyen_kg"          in ligne
            assert "duree_moyenne_minutes" in ligne

    @pytest.mark.asyncio
    async def test_lignes_limit_zero(self, client):
        response = await client.get("/lignes?limit=0")
        assert response.status_code == 200
