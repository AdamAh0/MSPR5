"""
Tests: Imports ETL
GET /imports
"""

import pytest


class TestImports:

    @pytest.mark.asyncio
    async def test_imports_status_200(self, client):
        response = await client.get('/imports')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_imports_retourne_pagination(self, client):
        response = await client.get('/imports')
        data = response.json()
        assert isinstance(data, dict)
        assert 'page' in data
        assert 'limit' in data
        assert 'total' in data
        assert 'imports' in data
        assert isinstance(data['imports'], list)

    @pytest.mark.asyncio
    async def test_imports_filtre_statut_succes(self, client):
        response = await client.get('/imports?statut=succès')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_imports_filtre_statut_echec(self, client):
        response = await client.get('/imports?statut=echec')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_imports_filtre_statut_partiel(self, client):
        response = await client.get('/imports?statut=partiel')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_imports_filtre_since(self, client):
        response = await client.get('/imports?since=2024-01-01T00:00:00Z')
        assert response.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_imports_statut_invalide(self, client):
        response = await client.get('/imports?statut=invalide')
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_imports_pagination_limit(self, client):
        response = await client.get('/imports?limit=5')
        assert response.status_code == 200
        assert len(response.json()['imports']) <= 5

    @pytest.mark.asyncio
    async def test_imports_limit_zero(self, client):
        response = await client.get('/imports?limit=0')
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_imports_champs_requis(self, client):
        response = await client.get('/imports?limit=1')
        data = response.json()
        if data['imports']:
            imp = data['imports'][0]
            assert 'id_import' in imp
            assert 'date_import' in imp
            assert 'statut' in imp
            assert 'nb_lignes_importees' in imp

    @pytest.mark.asyncio
    async def test_imports_nb_lignes_positif(self, client):
        response = await client.get('/imports')
        for imp in response.json()['imports']:
            assert imp['nb_lignes_importees'] >= 0


class TestImportsStats:

    @pytest.mark.asyncio
    async def test_imports_stats_status(self, client):
        response = await client.get('/imports/stats')
        assert response.status_code == 200
        data = response.json()
        assert 'total_imports' in data
        assert 'imports_reussis' in data
        assert 'imports_echoues' in data
        assert 'imports_partiels' in data
        assert 'taux_reussite' in data
        assert 'dernier_import' in data
        assert 'lignes_importees_total' in data
