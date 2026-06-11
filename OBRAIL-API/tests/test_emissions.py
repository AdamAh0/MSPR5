"""
Tests: Emissions CO2
GET /emissions/stats
"""

import pytest


class TestEmissions:

    @pytest.mark.asyncio
    async def test_emissions_stats_status(self, client):
        response = await client.get("/emissions/stats")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_emissions_stats_retourne_liste(self, client):
        response = await client.get("/emissions/stats")
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_emissions_stats_champs_requis_si_liste(self, client):
        response = await client.get("/emissions/stats")
        if response.json():
            data = response.json()[0]
            assert "operateur" in data
            assert "nb_trajets" in data
            assert "emission_moyenne_kg" in data

    @pytest.mark.asyncio
    async def test_emissions_stats_nb_trajets_positif_si_liste(self, client):
        response = await client.get("/emissions/stats")
        for stat in response.json():
            assert stat["nb_trajets"] >= 0
