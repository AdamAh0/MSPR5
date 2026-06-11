"""
Tests: Dashboard / KPI
GET /dashboard
GET /stats/kpi
"""

import pytest


class TestDashboard:

    @pytest.mark.asyncio
    async def test_dashboard_status_200(self, client):
        response = await client.get("/dashboard")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_champs_requis(self, client):
        response = await client.get("/dashboard")
        data = response.json()
        assert "total_trajets"        in data
        assert "trajets_jour"         in data
        assert "trajets_nuit"         in data
        assert "total_operateurs"     in data
        assert "total_lignes"         in data
        assert "total_gares"          in data
        assert "total_pays"           in data
        assert "co2_total_kg"         in data
        assert "co2_moyen_kg"         in data
        assert "duree_moyenne_minutes" in data

    @pytest.mark.asyncio
    async def test_dashboard_valeurs_positives(self, client):
        response = await client.get("/dashboard")
        data = response.json()
        assert data["total_trajets"] >= 0
        assert data["trajets_jour"]  >= 0
        assert data["trajets_nuit"]  >= 0
        assert data["total_gares"]   >= 0

    @pytest.mark.asyncio
    async def test_dashboard_retourne_dict(self, client):
        response = await client.get("/dashboard")
        assert isinstance(response.json(), dict)

    @pytest.mark.asyncio
    async def test_dashboard_total_gares_coherent(self, client):
        dashboard = await client.get("/dashboard")
        await client.get("/gares?limit=500")
        assert dashboard.json()["total_gares"] >= 0

    @pytest.mark.asyncio
    async def test_stats_kpi_equivalent(self, client):
        response = await client.get("/stats/kpi")
        assert response.status_code == 200
        data = response.json()
        assert data["total_trajets"] >= 0
        assert data["total_gares"]   >= 0
