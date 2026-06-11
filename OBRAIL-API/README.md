# OBRAIL-API — Observatoire ferroviaire européen

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0%2B-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B%20PostGIS-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![Tests](https://img.shields.io/badge/Tests-pytest-brightgreen)
![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-orange)

## Contexte

Ce projet s'inscrit dans le cadre du **MSPR** (Bloc E6.2), formation DIADS/DIA.  
L'API **OBRAIL Europe** est le backend central de l'observatoire des données ferroviaires européennes. Elle expose des endpoints REST asynchrones pour consulter les trajets, statistiques, opérateurs, lignes, gares, métriques environnementales, et **prédire la substituabilité avion → train** via un modèle de Machine Learning (Membre 3).

---

## Vue d'ensemble des endpoints

```
┌─────────────────────────────────────────────────────────────────┐
│                        OBRAIL API v3.0                          │
├─────────────────────────────────────────────────────────────────┤
│  Système                                                        │
│  GET  /health              → État de l'API + BDD                │
│                                                                 │
│  Trajets                                                        │
│  GET  /trajets             → Liste paginée avec filtres         │
│  GET  /trajets/{id}        → Détail d'un trajet                 │
│                                                                 │
│  Statistiques                                                   │
│  GET  /stats/kpi           → Chiffres clés globaux              │
│  GET  /stats/volumes       → Répartition par groupe             │
│  GET  /stats/comparatif-jour-nuit → Jour vs Nuit               │
│  GET  /stats/co2           → Émissions CO₂                      │
│  GET  /stats/top-liaisons  → Top liaisons fréquentées           │
│                                                                 │
│  Référentiels                                                   │
│  GET  /operateurs          → Opérateurs ferroviaires            │
│  GET  /lignes              → Lignes commerciales                │
│  GET  /gares               → Gares + géolocalisation            │
│  GET  /pays                → Référentiel pays                   │
│                                                                 │
│  Imports                                                        │
│  GET  /imports             → Historique des imports             │
│  GET  /imports/stats       → Métriques d'import                 │
│                                                                 │
│  IA / Prédiction  (Membre 3)                                    │
│  POST /predict             → Prédiction de substitution modale  │
│                                                                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                   ┌────────────┴────────────┐
                   │      PostgreSQL 15       │
                   │       + PostGIS          │
                   └─────────────────────────┘
```

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| **Framework** | FastAPI (asynchrone) |
| **Serveur ASGI** | Uvicorn |
| **Base de données** | PostgreSQL 15 + PostGIS |
| **Driver async** | `databases` (asyncpg) |
| **Validation** | Pydantic v2 |
| **ML / Inférence** | scikit-learn, joblib, numpy, pandas |
| **Tests** | pytest, httpx, pytest-asyncio, pytest-mock |
| **Configuration** | python-dotenv |
| **Conteneurisation** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions |

---

## Structure du projet

```
OBRAIL-API/
├── main.py                      # Point d'entrée — crée l'app, inclut les routers
│
├── database/
│   ├── __init__.py
│   └── connection.py            # Connexion PostgreSQL async + lifespan
│
├── utils/
│   ├── __init__.py
│   └── converters.py            # Fonctions utilitaires : to_float, to_iso, normalize_*
│
├── routers/
│   ├── trajets.py               # GET /trajets, GET /trajets/{id}
│   ├── stats.py                 # GET /stats/*
│   ├── referentiels.py          # GET /operateurs, /lignes, /gares, /pays
│   ├── imports.py               # GET /imports, /imports/stats
│   ├── predict.py               # POST /predict  ← Membre 3
│   └── compat.py                # Endpoints rétrocompatibles
│
├── schemas/
│   ├── __init__.py
│   └── predict.py               # Modèles Pydantic I/O pour /predict
│
├── services/
│   ├── __init__.py
│   └── predict_service.py       # Chargement du modèle ML + inférence
│
├── docs/
│   └── monitoring.md            # Guide de surveillance production (Membre 3)
│
├── tests/                       # Tests d'intégration (nécessitent une BDD)
│   ├── conftest.py
│   └── test_*.py
│
├── test_predict.py              # Tests unitaires POST /predict (mocks, sans BDD)
├── conftest.py                  # Fixtures pytest racine
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Installation & Démarrage

### Prérequis

- Python 3.10+ (ou Docker)
- PostgreSQL 15+ avec PostGIS (pour les endpoints BDD)

### Option 1 — Local (sans Docker)

**1. Configurer l'environnement :**

```powershell
copy .env.example .env
# Modifier DATABASE_URL dans .env
```

```env
DATABASE_URL=postgresql://obrail_user:obrail_pass@localhost:5433/obrail
```

**2. Installer les dépendances :**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**3. Lancer l'API :**

```powershell
python -m uvicorn main:app --reload
```

L'API démarre sur **http://localhost:8000**.  
Sans PostgreSQL, les routes BDD retournent une erreur mais `/predict` reste fonctionnel si un modèle est présent.

### Option 2 — Docker

```powershell
docker-compose up -d --build
```

---

## Documentation interactive

FastAPI génère automatiquement la documentation :

| Interface | URL |
|-----------|-----|
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |

---

## Endpoint IA — POST /predict

> **Ajout Membre 3** — Prédit la classe de substitution modale pour une ou plusieurs liaisons ferroviaires.

### Requête

```http
POST /predict
Content-Type: application/json
```

```json
[
  {
    "duree_minutes": 120.0,
    "heure_decimale": 8.5,
    "is_nuit": 0,
    "is_transfrontalier": 0,
    "code_pays_dep": "FR",
    "code_pays_arr": "FR"
  }
]
```

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `duree_minutes` | float | ≥ 0 | Durée du trajet en minutes |
| `heure_decimale` | float | 0 ≤ x < 24 | Heure de départ décimale (8.5 = 08h30) |
| `is_nuit` | int | 0 ou 1 | 1 si trajet de nuit |
| `is_transfrontalier` | int | 0 ou 1 | 1 si trajet transfrontalier |
| `code_pays_dep` | string | 2 caractères | Code ISO pays de départ |
| `code_pays_arr` | string | 2 caractères | Code ISO pays d'arrivée |

### Réponse

```json
{
  "results": [
    {
      "prediction": "substitution_possible",
      "proba_non_pertinent": 0.05,
      "proba_substitution_difficile": 0.15,
      "proba_substitution_possible": 0.80,
      "probabilities": {
        "non_pertinent": 0.05,
        "substitution_difficile": 0.15,
        "substitution_possible": 0.80
      }
    }
  ],
  "model_name": "mlp",
  "count": 1,
  "model_source": "artifacts/member3/best_model.joblib"
}
```

### Classes prédites

| Classe | Signification |
|--------|---------------|
| `non_pertinent` | Le train ne peut pas remplacer l'avion |
| `substitution_difficile` | Substitution possible mais contraignante |
| `substitution_possible` | Le train est une alternative crédible |

### Codes d'erreur

| Code | Cause |
|------|-------|
| 400 | Payload vide ou > 1 000 observations |
| 422 | Champ manquant ou invalide |
| 503 | Aucun modèle disponible (lancer l'entraînement d'abord) |
| 500 | Erreur interne |

### Modèle utilisé

L'API cherche le modèle dans cet ordre :
1. Variable d'environnement `MODEL_PATH`
2. `artifacts/member3/best_model.joblib` (MLP — Membre 3)
3. `../ia-mspr-/artifacts/member3/best_model.joblib`
4. `artifacts/member2/best_model.joblib` (classiques — Membre 2, fallback)

Pour pointer vers un modèle spécifique :

```powershell
$env:MODEL_PATH = "C:\...\artifacts\member3\best_model.joblib"
python -m uvicorn main:app --reload
```

---

## Endpoints détaillés

### GET /trajets

Liste paginée des trajets avec filtres.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `page` | int | Page (défaut: 1) |
| `limit` | int | Taille de page, max 100 (défaut: 15) |
| `id_operateur` | string | Filtrer par opérateur |
| `id_ligne` | string | Filtrer par ligne |
| `code_pays_depart` | string | Code ISO pays départ |
| `code_pays_arrivee` | string | Code ISO pays arrivée |
| `type` | string | `jour` ou `nuit` |
| `co2_max` | float | Émission CO₂ max (kg) |
| `duree_min` / `duree_max` | int | Plage de durée (minutes) |
| `search` | string | Recherche libre |

### GET /stats/kpi

```json
{
  "total_trajets": 52314,
  "trajets_jour": 48020,
  "trajets_nuit": 4294,
  "total_operateurs": 12,
  "total_lignes": 87,
  "total_gares": 142,
  "total_pays": 6,
  "co2_total_kg": 284156.3,
  "co2_moyen_kg": 5.43,
  "duree_moyenne_minutes": 116
}
```

### GET /stats/volumes?groupby=operateur

**Valeurs de `groupby`** : `operateur`, `ligne`, `pays_depart`, `pays_arrivee`, `jour_nuit`

### GET /gares

Supporte le filtrage par bounding box géographique :

```
GET /gares?bbox=43.0,2.0,49.0,8.0
```

Format : `lat_min,lng_min,lat_max,lng_max`

---

## Tests

### Tests unitaires (sans BDD)

```powershell
python -m pytest test_predict.py -v
```

9 tests couvrant la route `POST /predict` (mocks, validation, cas d'erreur).

### Tests d'intégration (avec BDD)

```powershell
python -m pytest tests/ -v --asyncio-mode=auto
```

### Couverture de code

```powershell
python -m pytest --cov=. --cov-report=html
# Rapport dans htmlcov/index.html
```

---

## Variables d'environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `DATABASE_URL` | Connexion PostgreSQL | `postgresql://user:pass@host:5433/db` |
| `MODEL_PATH` | Chemin vers le modèle `.joblib` (optionnel) | `artifacts/member3/best_model.joblib` |

---

## Architecture d'intégration

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  OBRAIL-Frontend │────▶│   OBRAIL-API     │────▶│   OBRAIL-BDD    │
│  (React/Vite)    │     │  (FastAPI)       │     │  (PostgreSQL)    │
│   Port 5173      │     │   Port 8000      │     │   Port 5433      │
└──────────────────┘     └────────┬─────────┘     └──────────────────┘
                                  │
                         ┌────────┴─────────┐
                         │   ia-mspr-       │
                         │  (Modèle ML)     │
                         │  .joblib         │
                         └──────────────────┘
```

---

## Surveillance (Membre 3)

Documentation complète dans [`docs/monitoring.md`](docs/monitoring.md) :

- Métriques de latence (Prometheus Histogram)
- Taux d'erreur par classe prédite
- Détection de data drift (test KS / PSI)
- Alertes et seuils recommandés

---

## CI/CD

Le workflow `.github/workflows/ci-api.yml` exécute automatiquement à chaque push :

1. Démarrage d'un container PostgreSQL/PostGIS
2. Initialisation du schéma BDD
3. Exécution de pytest avec couverture de code

---

## Licence

Projet pédagogique — Usage interne DIADS/DIA.
