# OBRAIL-API — Observatoire ferroviaire européen

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0%2B-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B%20PostGIS-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![Tests](https://img.shields.io/badge/Tests-pytest-brightgreen)
![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-orange)

## Contexte

Ce projet s'inscrit dans le cadre du **MSPR**, formation DIADS/DIA.
L'API **OBRAIL Europe** est le backend central de l'observatoire des données ferroviaires européennes. Elle expose des endpoints REST asynchrones pour consulter les trajets, statistiques, opérateurs, lignes, gares et métriques environnementales.

----

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                        OBRAIL API                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  GET /health              → État de l'API + BDD             │
│  GET /trajets             → Liste paginée avec filtres      │
│  GET /trajets/{id}        → Détail d'un trajet              │
│  GET /operateurs          → Opérateurs ferroviaires         │
│  GET /lignes              │ Lignes commerciales             │
│  GET /gares               → Gares + géolocalisation         │
│  GET /pays                → Référentiel pays                │
│                                                             │
│  GET /stats/kpi           → Chiffres clés globaux           │
│  GET /stats/volumes       → Répartition par groupe          │
│  GET /stats/comparatif    → Jour vs Nuit                    │
│  GET /stats/co2           → Émissions CO₂                   │
│  GET /stats/top-liaisons  → Top liaisons fréquentées        │
│                                                             │
│  GET /imports             → Historique des imports          │
│  GET /imports/stats       → Métriques d'import              │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │ PostgreSQL  │
                    │  + PostGIS  │
                    └─────────────┘
```

----

## Stack Technique

| Couche | Technologie |
|---|---|
| **Framework** | FastAPI (asynchrone) |
| **Serveur ASGI** | Uvicorn |
| **Base de données** | PostgreSQL 15 + PostGIS 3.4 |
| **ORM / Driver** | `databases` (asyncpg) + SQLAlchemy (core) |
| **Validation** | Pydantic v2 |
| **Tests** | pytest, httpx, pytest-mock, pytest-cov |
| **Configuration** | python-dotenv |
| **Conteneurisation** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions (lint, tests, build Docker) |

---

## Structure du projet

```
OBRAIL-API/
├── main.py              # Application FastAPI + tous les endpoints
├── requirements.txt     # Dépendances Python
├── Dockerfile           # Image Docker multi-stage
├── docker-compose.yml   # Orchestration API + BDD
├── .env.example         # Template de configuration
├── pytest.ini           # Configuration pytest
├── conftest.py          # Fixtures de test
├── tests/               # Tests unitaires et d'intégration
│   └── test_*.py
├── .github/workflows/   # Pipelines CI/CD
│   ├── ci-api.yml       # Tests Pytest avec BDD de test
│   └── docker-api.yml   # Build & push image Docker
├── .dockerignore        # Exclusions Docker
└── README.md            # Ce fichier
```

---

## Installation & Démarrage

### Prérequis

- Python 3.10+ ou Docker
- PostgreSQL 15+ avec extension PostGIS (si exécution locale)

### Option 1 : Docker (Recommandé)

```powershell
cd OBRAIL-API
docker-compose up -d --build
```

L'API est accessible sur **http://localhost:8000**.

### Option 2 : Environnement local

1. **Créer la base de données** (voir OBRAIL-BDD pour le script d'initialisation)

2. **Configurer les variables d'environnement** :
   ```powershell
   copy .env.example .env
   ```
   Modifier `DATABASE_URL` dans le fichier `.env` :
   ```env
   DATABASE_URL=postgresql+asyncpg://obrail_user:obrail_pass@localhost:5434/obrail
   ```

3. **Installer les dépendances** :
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Lancer le serveur** :
   ```powershell
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## Documentation de l'API

FastAPI génère automatiquement la documentation interactive :

| Interface | URL |
|---|---|
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |

---

## Endpoints détaillés

### Système & Santé

#### `GET /health`
Vérifie l'état de l'API et la connexion à la base de données.

```json
{
  "status": "ok",
  "timestamp": "2026-05-06T12:00:00Z",
  "components": {
    "db": "ok"
  }
}
```

### Trajets & Mobilité

#### `GET /trajets`
Liste paginée des trajets avec filtres.

**Paramètres de requête** :
| Paramètre | Type | Description |
|---|---|---|
| `page` | int | Numéro de page (défaut: 1) |
| `limit` | int | Taille de page (défaut: 15) |
| `operateur` | string | Filtrer par opérateur |
| `ligne` | string | Filtrer par ligne |
| `pays_depart` | string | Pays de départ |
| `pays_arrivee` | string | Pays d'arrivée |

#### `GET /trajets/{id_trajet}`
Détails complets d'un trajet avec gare de départ/arrivée, ligne et opérateur.

### Statistiques & KPIs

#### `GET /stats/kpi`
Chiffres clés globaux.

```json
{
  "total_trajets": 1250,
  "trajets_jour": 820,
  "trajets_nuit": 430,
  "total_operateurs": 5,
  "total_lignes": 28,
  "total_gares": 142,
  "total_pays": 12,
  "co2_total_kg": 3145.67,
  "co2_moyen_kg": 2.52,
  "duree_moyenne_minutes": 187
}
```

#### `GET /stats/volumes?groupby=operateur`
Répartition des volumes par catégorie.

**Paramètre `groupby`** : `operateur`, `ligne`, `pays_depart`, `creneau_horaire`

#### `GET /stats/comparatif-jour-nuit`
Comparaison détaillée jour vs nuit (nombre de trajets, durée moyenne, émissions CO₂).

#### `GET /stats/co2`
Statistiques environnementales par opérateur et par ligne.

### Référentiels

| Endpoint | Description |
|---|---|
| `GET /operateurs` | Liste des opérateurs ferroviaires |
| `GET /lignes` | Liste des lignes commerciales |
| `GET /gares` | Liste des gares (filtre par pays et bounding box) |
| `GET /pays` | Référentiel des pays couverts |

### Importation

| Endpoint | Description |
|---|---|
| `GET /imports` | Historique des imports avec pagination |
| `GET /imports/stats` | Métriques de réussite/échec des imports |

---

## Tests

### Exécuter les tests

```powershell
pytest tests/ --asyncio-mode=auto --cov=. --cov-report=html
```

### Pipeline CI des tests

Le workflow `ci-api.yml` exécute automatiquement les tests à chaque push/PR :

1. Clone le repo API + le repo BDD (pour le schéma SQL)
2. Lance un container PostgreSQL/PostGIS
3. Initialise la base avec le schéma
4. Exécute pytest avec couverture de code

---

## Docker

### Image Docker

Le Dockerfile utilise Python 3.11-slim pour une image légère :

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### CI/CD — Build & Push automatisé

Le workflow `docker-api.yml` construit et pousse l'image sur GHCR :

| Événement | Tag Docker |
|---|---|
| Push `main` | `ghcr.io/mspr-3/obrail-api:main` |
| Push `develop` | `ghcr.io/mspr-3/obrail-api:develop` |
| Tag `v1.2.0` | `ghcr.io/mspr-3/obrail-api:1.2.0` |
| PR #42 | `ghcr.io/mspr-3/obrail-api:pr-42` |

### Récupérer l'image

```powershell
docker pull ghcr.io/mspr-3/obrail-api:main
docker run -p 8000:8000 ghcr.io/mspr-3/obrail-api:main
```

---

## Architecture d'intégration

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  OBRAIL-Frontend │────▶│   OBRAIL-API     │────▶│   OBRAIL-BDD    │
│  (React/Vite)    │     │  (FastAPI)       │     │  (PostgreSQL)    │
│   Port 5173      │     │   Port 8000      │     │   Port 5434      │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## Configuration avancée

### Variables d'environnement

| Variable | Description | Exemple |
|---|---|---|
| `DATABASE_URL` | Chaîne de connexion asyncpg | `postgresql+asyncpg://user:pass@host:5432/db` |

### CORS & Sécurité

L'API peut être configurée avec des middlewares CORS pour restreindre les origines autorisées.

---

## Qualité de code

### Husky + Hooks

Le projet utilise Husky pour exécuter des vérifications avant chaque commit.

### Conventions

- Code asynchrone avec `async/await`
- Validation Pydantic pour tous les schémas de réponse
- Tests couvrant les endpoints critiques

---

## Licence

Projet pédagogique. Usage interne — DIADS/DIA.
