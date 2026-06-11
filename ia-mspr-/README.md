# MSPR ObRail — Pipeline IA (Bloc E6.2)

Modèle prédictif de **substitution modale avion → train** appliqué au référentiel de trajets ferroviaires **ObRail** (base PostgreSQL/PostGIS alimentée par ETL, exposée via une API FastAPI).

**Objectif** : classifier chaque liaison ferroviaire en trois catégories — `non_pertinent`, `substitution_difficile`, `substitution_possible` — afin d'identifier les trajets ferroviaires pouvant remplacer des vols aériens dans le cadre du Green Deal européen.

---

## Équipe & répartition des étapes

| Membre | Rôle | Étapes |
|--------|------|--------|
| **M1** — Data Analyst / ML Lead | EDA, préparation des données | 1 · Business → 2 · Analyse → 3 · Préparation |
| **M2** — ML Engineer (classiques) | Modèles classiques, évaluation | 3 · Préparation → 4 · Modélisation → 5 · Évaluation → 6 · Déploiement |
| **M3** — ML Engineer (MLP) | Réseau de neurones, intégration API | 3 → 4 → 5 → 6 · Déploiement → 7 · Surveillance |
| **M4** — Cloud & MLOps | Services cloud, RGPD, veille | 3 → 4 → 5 → 6 → 7 |
| **M5** — Chef de projet / Tech Writer | CI/CD, rapport, soutenance | 1 · Business → 5 → 6 → 7 |

---

## Structure du projet

```
ia-mspr-/
├── data/
│   ├── obrail_trajets.csv          # Dataset brut (52 314 services, extrait BDD)
│   └── obrail_features.csv         # Dataset préparé (sortie M1, entrée M2/M3)
│
├── notebooks/
│   ├── 01_eda.ipynb                # M1 — Analyse exploratoire (EDA)
│   ├── 02_preparation.ipynb        # M1 — Nettoyage + feature engineering
│   └── 02b_cible_substitution.ipynb # M1 — Construction de la variable cible
│
├── docs/
│   ├── 01_business.md              # M1 — Spécifications fonctionnelles, justification IA
│   └── 02_rapport_projet.md        # Vue d'ensemble de l'architecture du projet
│
├── artifacts/
│   ├── member2/                    # Artefacts M2 (modèles classiques)
│   │   ├── best_model.joblib       # Meilleur modèle sérialisé
│   │   ├── candidate_results.csv   # Tableau comparatif des modèles
│   │   ├── training_summary.json   # Métriques finales
│   │   ├── confusion_matrix_test.png
│   │   └── feature_importance.png
│   │
│   └── member3/                    # Artefacts M3 (MLP)
│       ├── best_model.joblib       # Modèle MLP sérialisé
│       ├── training_summary.json   # Métriques finales
│       ├── confusion_matrix_test.png
│       ├── loss_curve.png          # Courbe de perte par époque
│       └── model_comparison.png    # Comparaison M2 vs M3
│
├── member2_ml.py                   # M2 — Pipeline ML classiques (LR, RF, XGBoost, LightGBM)
├── member3_mlp.py                  # M3 — Pipeline MLP (réseau de neurones)
├── predict.py                      # Script d'inférence en ligne de commande
├── sample.json                     # Payload de test pour predict.py
├── requirements.txt
└── README.md
```

---

## Variables du modèle

### Features (entrées)

| Variable | Type | Description |
|----------|------|-------------|
| `duree_minutes` | Numérique | Durée du trajet en minutes |
| `heure_decimale` | Numérique | Heure de départ en décimal (ex: 8.5 = 08h30) |
| `is_nuit` | Binaire | 1 si trajet de nuit (départ ≥ 18h) |
| `is_transfrontalier` | Binaire | 1 si le trajet traverse une frontière |
| `code_pays_dep` | Catégorielle | Code ISO du pays de départ (ex: FR, DE) |
| `code_pays_arr` | Catégorielle | Code ISO du pays d'arrivée |

### Cible (sortie)

| Classe | Signification |
|--------|---------------|
| `non_pertinent` | Le train ne peut pas se substituer à l'avion |
| `substitution_difficile` | Substitution possible mais contraignante |
| `substitution_possible` | Le train est une alternative crédible à l'avion |

---

## Installation

```powershell
# Créer un environnement virtuel (hors OneDrive pour éviter les conflits)
python -m venv C:\Users\<user>\.venvs\mspr-obrail
C:\Users\<user>\.venvs\mspr-obrail\Scripts\Activate.ps1

pip install -r requirements.txt
```

---

## Utilisation

### M1 — Analyse exploratoire

Ouvrir les notebooks dans VS Code ou Jupyter :

```powershell
jupyter notebook notebooks/01_eda.ipynb
```

### M2 — Entraînement des modèles classiques

```powershell
python member2_ml.py --data data/obrail_features.csv --artifact-dir artifacts/member2
```

Modèles entraînés : Régression Logistique (baseline), Random Forest, XGBoost, LightGBM.  
Résultats dans `artifacts/member2/candidate_results.csv`.

### M3 — Entraînement du MLP

```powershell
# Recherche rapide (3 architectures, pour test)
python member3_mlp.py --n-iter 3 --cv-splits 3

# Recherche complète (20 architectures, recommandé)
python member3_mlp.py --n-iter 20 --cv-splits 5
```

**Résultats obtenus avec `--n-iter 3`** :

| Métrique | Score |
|----------|-------|
| Accuracy (test) | 93.6 % |
| F1-macro (test) | 77.9 % |
| AUC-ROC (test) | 96.8 % |

Meilleure architecture : **(256, 128, 64)** — activation relu, α=0.0005, lr=0.001

### Prédiction en ligne de commande

```powershell
python predict.py --model artifacts/member3/best_model.joblib --payload sample.json
```

---

## Architectures MLP testées (M3)

La recherche d'architecture couvre les configurations suivantes via `RandomizedSearchCV` :

| Hyperparamètre | Valeurs |
|----------------|---------|
| `hidden_layer_sizes` | (64,), (128,), (256,), (64,32), (128,64), (256,128), (128,64,32), (256,128,64), (512,256,128) |
| `activation` | relu, tanh |
| `alpha` (régularisation L2) | 1e-4, 5e-4, 1e-3, 5e-3, 1e-2 |
| `learning_rate_init` | 1e-3, 5e-3, 1e-2 |
| `batch_size` | 64, 128, 256 |

Validation croisée stratifiée 5-fold, optimisation sur F1-macro.

---

## Preprocessing (commun M2 et M3)

```
Variables numériques  →  SimpleImputer(median)  →  StandardScaler
Variables catégorielles  →  SimpleImputer(most_frequent)  →  OneHotEncoder
```

Le pipeline scikit-learn est intégré dans le fichier `.joblib` pour garantir que le preprocessing est appliqué de manière identique en entraînement et en production.

---

## Format de l'artefact modèle

Les fichiers `.joblib` exportés par M2 et M3 ont la structure suivante :

```python
{
    "model_name": "mlp",          # ou "random_forest", "xgboost", etc.
    "pipeline": Pipeline,          # pipeline sklearn complet (preprocessing + modèle)
    "label_encoder": LabelEncoder, # encodeur des classes cibles
    "class_names": [...],          # liste des classes dans l'ordre
    "feature_columns": [...],      # noms des colonnes attendues en entrée
    "test_metrics": {...},         # accuracy, f1_macro, roc_auc, matrice de confusion
    ...
}
```

Ce format est compatible avec la route `POST /predict` de l'API OBRAIL.

---

## Données

- **Source** : dépôt `OBRAIL-BDD` (`db/init_obrail_db.sql`), table `trajet` jointe à `gare`, `ligne`, `operateur`.
- **Limites connues** (cf. EDA) : `distance_km` manquante ~55 %, jointure `operateur` ~100 % nulle, gares manquantes ~47 %, quelques CO₂ négatifs / durées nulles.
- **Déséquilibre des classes** : `non_pertinent` représente ~88 % du jeu étiqueté → les modèles utilisent `class_weight='balanced'` et sont évalués sur F1-macro.
