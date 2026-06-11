"""
Tests: Racine de l'API
GET /
"""

import pytest


class TestRacine:

    @pytest.mark.asyncio
    async def test_root_status_200(self, client):
        response = await client.get("/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_root_contient_api(self, client):
        response = await client.get("/")
        assert response.json()["api"] == "ObRail Europe"

    @pytest.mark.asyncio
    async def test_root_contient_version(self, client):
        response = await client.get("/")
        assert "version" in response.json()

    @pytest.mark.asyncio
    async def test_root_contient_endpoints(self, client):
        response = await client.get("/")
        data = response.json()
        assert "endpoints" in data
        assert "/stats/kpi" in data["endpoints"]
        assert "/health"    in data["endpoints"]

    @pytest.mark.asyncio
    async def test_root_contient_documentation(self, client):
        response = await client.get("/")
        assert "documentation" in response.json()

    @pytest.mark.asyncio
    async def test_route_inexistante_404(self, client):
        response = await client.get("/route_inexistante")
        assert response.status_code == 404
