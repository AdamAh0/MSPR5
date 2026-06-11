"""
Tests: Op?rateurs
GET /operateurs
"""

import pytest


class TestOperateurs:

    @pytest.mark.asyncio
    async def test_operateurs_status_200(self, client):
        response = await client.get("/operateurs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_operateurs_retourne_conteneur(self, client):
        response = await client.get("/operateurs")
        data = response.json()
        assert isinstance(data, dict)
        assert "operateurs" in data
        assert isinstance(data["operateurs"], list)

    @pytest.mark.asyncio
    async def test_operateurs_champs_requis(self, client):
        response = await client.get("/operateurs")
        data = response.json()
        if data["operateurs"]:
            op = data["operateurs"][0]
            assert "id_operateur" in op
            assert "nom" in op
            assert "nb_trajets" in op
            assert "nb_lignes" in op

    @pytest.mark.asyncio
    async def test_operateurs_tries_par_nb_trajets(self, client):
        response = await client.get("/operateurs")
        data = response.json()["operateurs"]
        if len(data) > 1:
            trajets = [o["nb_trajets"] for o in data]
            assert trajets == sorted(trajets, reverse=True)

    @pytest.mark.asyncio
    async def test_operateurs_nb_trajets_positif(self, client):
        response = await client.get("/operateurs")
        for op in response.json()["operateurs"]:
            assert op["nb_trajets"] >= 0
