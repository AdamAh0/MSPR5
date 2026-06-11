# Rapport des modifications — Membre 3

**Date** : 2026-06-11  
**Périmètre** : Étapes 3, 4, 5, 6, 7 — ML Engineer (MLP) + Intégration API  

---

## 1. Résumé des travaux réalisés

| Étape | Livrable | Statut |
|-------|----------|--------|
| 3 – Data préparation | Vérification compatibilité NN (`member3_mlp.py::validate_nn_compatibility`) | ✅ |
| 4 – Modélisation | MLP avec `RandomizedSearchCV` sur 9 architectures, 5-fold CV | ✅ |
| 5 – Évaluation | Courbe de loss, matrice de confusion, comparaison M2 vs M3 | ✅ |
| 6 – Déploiement | Route `POST /predict` dans l'API FastAPI + refactorisation | ✅ |
| 7 – Surveillance | Documentation monitoring (`docs/monitoring.md`) | ✅ |
| Bonus | Refactorisation complète de l'API en modules | ✅ |

---

## 2. Nouveaux fichiers créés

### 2.1 Projet IA — `ia-mspr-/`

| Fichier | Rôle |
|---------|------|
| `member3_mlp.py` | Pipeline complet d'entraînement MLP |
| `artifacts/member3/` | Dossier de sortie des artefacts M3 (créé, vide avant exécution) |

### 2.2 API — `OBRAIL-API/`

**Structure modulaire :**

```
OBRAIL-API/
├── main.py                      (refactorisé — ~90 lignes au lieu de 1 077)
├── database/
│   ├── __init__.py
│   └── connection.py            (DATABASE_URL, database, lifespan)
├── utils/
│   ├── __init__.py
│   └── converters.py            (to_float, to_iso, normalize_*, parse_bbox)
├── routers/
│   ├── __init__.py
│   ├── trajets.py               (GET /trajets, GET /trajets/{id})
│   ├── stats.py                 (GET /stats/*)
│   ├── referentiels.py          (GET /operateurs, /lignes, /gares, /pays)
│   ├── imports.py               (GET /imports, /imports/stats)
│   ├── predict.py               (POST /predict — NOUVEAU)
│   └── compat.py                (GET /dashboard, /emissions/stats, /localisations)
├── schemas/
│   ├── __init__.py
│   └── predict.py               (PredictInput, PredictResult, PredictResponse)
├── services/
│   ├── __init__.py
│   └── predict_service.py       (chargement modèle, inférence)
├── test_predict.py              (9 tests pytest pour POST /predict)
├── docs/
│   └── monitoring.md            (métriques de surveillance production)
└── requirements.txt             (mis à jour avec scikit-learn, joblib, numpy, pandas)
```

---

## 3. Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `OBRAIL-API/main.py` | Refactorisé de 1 077 lignes → ~90 lignes (thin entry point) |
| `OBRAIL-API/requirements.txt` | Ajout de `scikit-learn`, `joblib`, `numpy`, `pandas`, `pytest-asyncio` |

---

## 4. Description détaillée des modifications

### 4.1 `member3_mlp.py` — Pipeline MLP (Étapes 3, 4, 5)

**Étape 3 — Vérification compatibilité NN**

La fonction `validate_nn_compatibility()` vérifie :
- Présence de toutes les colonnes requises
- Distribution des variables numériques (mean, std, nulls)
- Nombre de modalités des variables catégorielles (OneHotEncoding)
- Taille des splits train/val/test
- Distribution des classes cibles (détection déséquilibre)

**Étape 4 — Architecture MLP**

`MLPClassifier` (scikit-learn) avec `RandomizedSearchCV` sur :

| Hyperparamètre | Valeurs testées |
|----------------|-----------------|
| `hidden_layer_sizes` | (64,), (128,), (256,), (64,32), (128,64), (256,128), (128,64,32), (256,128,64), (512,256,128) |
| `activation` | relu, tanh |
| `alpha` | 1e-4, 5e-4, 1e-3, 5e-3, 1e-2 |
| `learning_rate_init` | 1e-3, 5e-3, 1e-2 |
| `batch_size` | 64, 128, 256 |

- Preprocessing identique à M2 : `StandardScaler` pour les numériques, `OneHotEncoder` pour les catégorielles
- `early_stopping=True` pendant la recherche, puis ré-entraînement sans pour capturer la `loss_curve_`

**Étape 5 — Visualisations produites dans `artifacts/member3/`**

| Fichier | Contenu |
|---------|---------|
| `confusion_matrix_test.png` | Matrice de confusion sur le jeu de test |
| `loss_curve.png` | Courbe de perte par époque |
| `model_comparison.png` | Comparaison accuracy / F1-macro / AUC entre M2 et M3 |
| `training_summary.json` | Métriques val + test, hyperparamètres retenus |
| `best_model.joblib` | Artefact modèle (même format que M2) |

---

### 4.2 Route `POST /predict` — Intégration API (Étape 6)

**Endpoint** : `POST /predict`

**Corps de la requête** (JSON) :
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

**Réponse** (JSON) :
```json
{
  "results": [
    {
      "prediction": "substitution_possible",
      "proba_non_pertinent": 0.05,
      "proba_substitution_difficile": 0.15,
      "proba_substitution_possible": 0.80,
      "probabilities": { "non_pertinent": 0.05, ... }
    }
  ],
  "model_name": "mlp",
  "count": 1,
  "model_source": "artifacts/member3/best_model.joblib"
}
```

**Priorité de chargement du modèle** :
1. Variable d'environnement `MODEL_PATH`
2. `artifacts/member3/best_model.joblib` (M3 — MLP)
3. `../ia-mspr-/artifacts/member3/best_model.joblib`
4. `artifacts/member2/best_model.joblib` (M2 — fallback)
5. `../ia-mspr-/artifacts/member2/best_model.joblib`

**Codes d'erreur** :

| Code | Cause |
|------|-------|
| 400 | Payload vide ou > 1000 observations |
| 422 | Champ manquant ou invalide (code pays > 2 chars, durée < 0, etc.) |
| 503 | Aucun fichier modèle disponible |
| 500 | Erreur interne inattendue |

---

### 4.3 Refactorisation de l'API (Étape 6 — bonus)

**Avant** : `main.py` de 1 077 lignes monolithiques.

**Après** : architecture modulaire en 5 couches.

**Choix d'architecture** :

- **`database/`** : isoler la connexion PostgreSQL du reste du code. Facilite le mock en tests et le remplacement par un autre moteur.
- **`utils/`** : fonctions pures sans dépendance FastAPI sauf HTTPException. Testables unitairement.
- **`routers/`** : un fichier par domaine métier. Chaque router importe uniquement ce dont il a besoin.
- **`schemas/`** : modèles Pydantic séparés pour une validation claire des I/O de l'API IA.
- **`services/`** : logique d'inférence ML découplée du router HTTP (modèle chargé en cache mémoire, remplaçable sans toucher au router).

**Rétrocompatibilité** : les tests existants (`conftest.py` importe `from main import app`) continuent de fonctionner sans modification.

**CORS** : `allow_methods` étendu à `["GET", "POST"]` pour autoriser la nouvelle route.

---

### 4.4 Surveillance (Étape 7)

Documentation complète dans `OBRAIL-API/docs/monitoring.md` couvrant :
- Métriques de latence (Histogram Prometheus)
- Taux d'erreur par classe prédite (Counter Prometheus)
- Détection de data drift (test KS / PSI par feature)
- Métriques de fiabilité du modèle
- Architecture de collecte recommandée (Prometheus + Loki)
- Exemple d'intégration `prometheus-fastapi-instrumentator`
- Seuils d'alerte et actions correctives

---

## 5. Points restants / améliorations possibles

| Priorité | Point |
|----------|-------|
| Haute | Entraîner réellement le MLP (`python member3_mlp.py`) et vérifier les métriques |
| Haute | Intégrer `prometheus-fastapi-instrumentator` en production |
| Moyenne | Ajouter le logging structuré JSON (structlog) |
| Moyenne | Implémenter la détection de data drift automatique en production |
| Moyenne | Ajouter des tests d'intégration pour `/predict` avec un vrai modèle léger |
| Basse | Essayer Keras/TensorFlow pour un MLP avec dropout si scikit-learn insuffisant |
| Basse | Exposer un endpoint `GET /predict/info` retournant les métriques du modèle chargé |

---

## 6. Instructions d'utilisation

### Entraîner le MLP (depuis `ia-mspr-/`)

```bash
cd ia-mspr-
python member3_mlp.py --data data/obrail_features.csv --n-iter 20
# Artefacts dans artifacts/member3/
```

### Lancer l'API (depuis `OBRAIL-API/`)

```bash
cd OBRAIL-API
uvicorn main:app --reload
```

### Tester la route /predict

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '[{"duree_minutes":120,"heure_decimale":8.5,"is_nuit":0,"is_transfrontalier":0,"code_pays_dep":"FR","code_pays_arr":"FR"}]'
```

### Exécuter les tests

```bash
cd OBRAIL-API
pytest test_predict.py -v
pytest -v  # tous les tests
```

---

## 7. Dépendances ajoutées

| Package | Version | Raison |
|---------|---------|--------|
| `scikit-learn>=1.3.0` | ML | MLPClassifier, pipeline d'inférence |
| `joblib>=1.3.0` | ML | Sérialisation/désérialisation des modèles |
| `numpy>=1.24.0` | ML | Calcul des probabilités |
| `pandas>=2.0.0` | ML | Préparation du payload pour l'inférence |
| `pytest-asyncio>=0.23.0` | Tests | Tests async déjà utilisés mais non déclaré |
