# Surveillance & Monitoring — Route POST /predict

## Métriques de production pertinentes

### 1. Latence

| Métrique | Description | Seuil d'alerte |
|----------|-------------|----------------|
| `predict_latency_ms` | Temps de réponse de la route `/predict` en ms | > 500 ms |
| `predict_latency_p99` | 99e percentile de latence | > 1 000 ms |

**Collecte** : la route `/predict` logue déjà la latence via `logger.info(...)`. Pour une collecte Prometheus :

```python
from prometheus_client import Histogram
PREDICT_LATENCY = Histogram("predict_latency_seconds", "Latence POST /predict", buckets=[.05, .1, .25, .5, 1, 2.5])

@router.post("/predict")
async def post_predict(payload: list[PredictInput]):
    with PREDICT_LATENCY.time():
        ...
```

---

### 2. Taux d'erreur par classe (class error rate)

Surveiller la distribution des classes prédites permet de détecter un déséquilibre anormal (ex. : le modèle prédit toujours `non_pertinent`).

| Métrique | Description |
|----------|-------------|
| `predict_class_count{class="non_pertinent"}` | Nombre de prédictions par classe |
| `predict_class_count{class="substitution_difficile"}` | |
| `predict_class_count{class="substitution_possible"}` | |

**Collecte** :

```python
from prometheus_client import Counter
PREDICT_CLASS = Counter("predict_class_count", "Prédictions par classe", ["class_name"])

# Dans post_predict, après avoir obtenu les résultats :
for r in raw["results"]:
    PREDICT_CLASS.labels(class_name=r["prediction"]).inc()
```

---

### 3. Data drift (dérive des données)

Le data drift survient quand les caractéristiques des données en production s'éloignent de celles utilisées pour l'entraînement.

| Caractéristique | Méthode de détection |
|-----------------|----------------------|
| `duree_minutes` | Test de Kolmogorov-Smirnov vs distribution d'entraînement |
| `heure_decimale` | Test KS |
| `is_transfrontalier` | Test chi² |
| `code_pays_dep` / `code_pays_arr` | Distribution des fréquences, PSI (Population Stability Index) |

**Approche pratique** :

```python
# Sauvegarder les statistiques de référence lors de l'entraînement
import json
from pathlib import Path

reference_stats = {
    "duree_minutes": {"mean": X_train["duree_minutes"].mean(), "std": X_train["duree_minutes"].std()},
    ...
}
Path("artifacts/member3/reference_stats.json").write_text(json.dumps(reference_stats))
```

En production, collecter un buffer des dernières requêtes et lancer un test toutes les N prédictions (ex. N=1000).

---

### 4. Métriques de fiabilité

| Métrique | Description |
|----------|-------------|
| `predict_error_rate` | Proportion de requêtes en erreur 5xx |
| `predict_requests_total` | Volume total de requêtes |
| `model_load_status` | Statut du chargement du modèle (1=OK, 0=KO) |

---

## Architecture de collecte recommandée

```
FastAPI /predict
    │
    ├── logs structurés (JSON) → Loki / Elasticsearch
    │       • timestamp, n_observations, latency_ms, model_name, predictions_dist
    │
    ├── métriques Prometheus (/metrics)
    │       • latence (histogram)
    │       • taux d'erreur (counter)
    │       • distribution de classes (counter)
    │
    └── data drift batch (cron toutes les heures)
            • lecture des logs de la dernière heure
            • calcul PSI / KS sur les features
            • alerte si PSI > 0.2 (drift significatif)
```

### Intégration Prometheus (exemple minimal)

Installer `prometheus-fastapi-instrumentator` :

```bash
pip install prometheus-fastapi-instrumentator
```

Dans `main.py` :

```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

Cela expose `/metrics` avec les métriques HTTP standard (latence, status codes, etc.).

---

## Logging structuré (FastAPI)

La route `/predict` produit déjà des logs de la forme :

```
POST /predict | n=2 | latence=12.3ms | model=mlp
```

Pour un logging JSON structuré compatible avec des outils d'observabilité :

```python
import structlog
logger = structlog.get_logger()
logger.info("predict", n=len(payload), latency_ms=latency_ms, model=raw["model_name"])
```

---

## Alertes recommandées

| Condition | Action |
|-----------|--------|
| Latence p99 > 1s pendant 5 min | Alerte PagerDuty / Slack |
| Taux d'erreur > 5% | Alerte immédiate |
| Classe dominante > 95% des prédictions | Investigation data drift |
| PSI feature > 0.2 | Déclencher ré-entraînement |
| `model_load_status = 0` | Alerte critique, rollback |
