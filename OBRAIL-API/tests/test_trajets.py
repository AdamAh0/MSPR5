"""
Tests: Trajets
GET /trajets
GET /trajets/{id_trajet}
"""

import pytest


class TestTrajetsListe:

    @pytest.mark.asyncio
    async def test_trajets_status(self, client):
        response = await client.get("/trajets")
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_trajets_retourne_pagination(self, client):
        response = await client.get('/trajets')
        data = response.json()
        assert isinstance(data, dict)
        assert 'page' in data
        assert 'limit' in data
        assert 'total' in data
        assert 'total_pages' in data
        assert 'results' in data
        assert isinstance(data['results'], list)

    @pytest.mark.asyncio
    async def test_trajets_filtres_compatibles(self, client):
        response = await client.get('/trajets?page=1&limit=10&type=jour&co2_max=50&duree_max=600')
        assert response.status_code == 200
        data = response.json()
        assert data['page'] == 1
        assert data['limit'] == 10
        assert len(data['results']) <= 10

    @pytest.mark.asyncio
    async def test_trajets_filtre_code_pays_depart(self, client):
        response = await client.get('/trajets?code_pays_depart=FR')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_trajets_filtre_code_pays_arrivee(self, client):
        response = await client.get('/trajets?code_pays_arrivee=DE')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_trajets_pagination_limit(self, client):
        response = await client.get('/trajets?page=1&limit=5')
        assert response.status_code == 200
        assert len(response.json()['results']) <= 5

    @pytest.mark.asyncio
    async def test_trajets_champs_requis(self, client):
        response = await client.get('/trajets?page=1&limit=1')
        data = response.json()
        if data['results']:
            trajet = data['results'][0]
            assert 'id_trajet' in trajet
            assert 'id_service' in trajet
            assert 'depart' in trajet
            assert 'arrivee' in trajet
            assert 'heure_depart' in trajet
            assert 'heure_arrivee' in trajet
            assert 'duree_minutes' in trajet
            assert 'type_calcul' in trajet
            assert 'emission_co2_kg' in trajet
            assert 'ligne' in trajet
            assert 'operateur' in trajet


class TestTrajetsErreurs:

    @pytest.mark.asyncio
    async def test_trajets_limit_zero(self, client):
        response = await client.get('/trajets?limit=0')
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_trajets_limit_trop_grand(self, client):
        response = await client.get('/trajets?limit=9999')
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_trajets_duree_max_negative(self, client):
        response = await client.get('/trajets?duree_max=-1')
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_trajets_co2_max_negative(self, client):
        response = await client.get('/trajets?co2_max=-10')
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_trajet_id_non_existant(self, client):
        response = await client.get('/trajets/99999')
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_trajet_erreur_contient_detail(self, client):
        response = await client.get('/trajets/99999')
        assert response.status_code == 404
        assert 'detail' in response.json()


class TestTrajetDetail:

    @pytest.mark.asyncio
    async def test_trajet_par_id_champs(self, client):
        response = await client.get('/trajets/1')
        if response.status_code == 200:
            data = response.json()
            assert 'id_trajet' in data
            assert 'id_service' in data
            assert 'depart' in data
            assert 'arrivee' in data
            assert 'heure_depart' in data
            assert 'heure_arrivee' in data
            assert 'duree_minutes' in data
            assert 'type_calcul' in data
            assert 'ligne' in data
            assert 'operateur' in data
