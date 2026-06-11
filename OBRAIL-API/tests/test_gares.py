"""
Tests: Gares
GET /gares
GET /gares/{id_gare}
"""

import pytest


class TestGaresListe:

    @pytest.mark.asyncio
    async def test_gares_status(self, client):
        response = await client.get("/gares")
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_gares_retourne_conteneur(self, client):
        response = await client.get("/gares")
        data = response.json()
        assert isinstance(data, dict)
        assert "gares" in data
        assert isinstance(data["gares"], list)

    @pytest.mark.asyncio
    async def test_gares_filtre_code_pays(self, client):
        response = await client.get("/gares?code_pays=FR")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gares_filtre_code_pays_de(self, client):
        response = await client.get("/gares?code_pays=DE")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gares_filtre_ville(self, client):
        response = await client.get("/gares?search=Paris")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gares_filtre_type_nationale(self, client):
        response = await client.get("/gares?type_liaison=nationale")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gares_filtre_type_internationale(self, client):
        response = await client.get("/gares?type_liaison=internationale")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gares_filtre_type_regionale(self, client):
        response = await client.get("/gares?type_liaison=r?gionale")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gares_code_pays_minuscule(self, client):
        response = await client.get("/gares?code_pays=fr")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gares_bbox(self, client):
        response = await client.get("/gares?bbox=40,0,60,20")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gares_champs_requis(self, client):
        response = await client.get("/gares")
        data = response.json()
        if data["gares"]:
            gare = data["gares"][0]
            assert "id_gare" in gare
            assert "nom_officiel" in gare
            assert "code_pays" in gare
            assert "ville" in gare
            assert "type_liaison" in gare
            assert "nb_departs" in gare
            assert "nb_arrivees" in gare


class TestGaresErreurs:

    @pytest.mark.asyncio
    async def test_gares_code_pays_invalide(self, client):
        response = await client.get("/gares?code_pays=FRANCE")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gares_type_liaison_invalide(self, client):
        response = await client.get("/gares?type_liaison=invalide")
        assert response.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_gares_limit_zero(self, client):
        response = await client.get("/gares?limit=0")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_gare_non_existante_404(self, client):
        response = await client.get("/gares/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_gare_erreur_contient_detail(self, client):
        response = await client.get("/gares/99999")
        assert "detail" in response.json()


class TestGareDetail:

    @pytest.mark.asyncio
    async def test_gare_par_id_champs(self, client):
        response = await client.get("/gares/1")
        if response.status_code == 200:
            data = response.json()
            assert "id_gare" in data
            assert "nom_officiel" in data
            assert "code_pays" in data
            assert "ville" in data
