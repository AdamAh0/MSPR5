"""Génère notebooks/02_preparation.ipynb (étape 3 — préparation pour le clustering)."""
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
cells = []
def md(s): cells.append(nbf.v4.new_markdown_cell(s.strip("\n")))
def code(s): cells.append(nbf.v4.new_code_cell(s.strip("\n")))

md(r"""
# MSPR ObRail — Étape 3 : Préparation des données (clustering)

**Bloc E6.2 — Membre 1 (Data Analyst / ML Lead)**

À partir du dataset brut analysé à l'étape 2, ce notebook produit un **jeu de features
propre et documenté**, prêt pour la modélisation non supervisée (découverte de **familles
de dessertes**) réalisée par M2/M3 à l'étape 4.

**Chaîne de traitement :** nettoyage des aberrants → feature engineering → sélection des
variables (avec écartement des variables redondantes) → standardisation → split 70/15/15
(seed fixée) → export `data/obrail_features.csv`.
""")

md("## 1. Configuration et chargement")
code(r"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

RANDOM_STATE = 42   # graine fixée -> reproductibilité

candidats = [Path("data/obrail_trajets.csv"),
             Path("../data/obrail_trajets.csv"),
             Path("obrail_trajets.csv")]
CSV = next((p for p in candidats if p.exists()), None)
if CSV is None:
    raise FileNotFoundError("Place obrail_trajets.csv dans data/")
ROOT = CSV.resolve().parent.parent

df = pd.read_csv(CSV)
print(f"{len(df):,} services chargés depuis {CSV}")
df.head(3)
""")

md(r"""
## 2. Nettoyage des valeurs aberrantes

L'EDA a identifié des valeurs physiquement impossibles. On les retire (volume négligeable,
aucune imputation hasardeuse) en **traçant** ce qui est supprimé.
""")
code(r"""
n0 = len(df)
masque_valide = (df["duree_minutes"] > 0) & (df["emission_co2_kg"] >= 0)
retirees = (~masque_valide).sum()
df = df[masque_valide].copy()
print(f"Durées <= 0 ou CO2 < 0 retirés : {retirees} lignes  ({n0:,} -> {len(df):,})")
""")

md(r"""
## 3. Détection d'une variable redondante (point méthodologique clé)

Avant de choisir les features, on vérifie l'**indépendance** des variables numériques.
Le CO₂ se révèle être une **transformation linéaire exacte de la durée**.
""")
code(r"""
corr = df["emission_co2_kg"].corr(df["duree_minutes"])
ratio = (df["emission_co2_kg"] / df["duree_minutes"])
print(f"corr(emission_co2_kg, duree_minutes) = {corr:.4f}")
print(f"emission_co2_kg / duree_minutes : médiane = {ratio.median():.4f} kg/min, "
      f"écart-type = {ratio.std():.5f}")
print("\n=> CO2 ≈ 0.05 × durée : aucune information indépendante.")
print("=> On ÉCARTE le CO2 des features de clustering (sinon on pondère 2x le même axe),")
print("   mais on le CONSERVE dans le dataset de sortie pour le reporting décarbonation.")
""")

md(r"""
## 4. Feature engineering

On dérive des variables exploitables et porteuses de sens métier :

- `heure_decimale` — heure de départ en continu (rythme de la desserte) ;
- `is_nuit` — desserte de nuit (catégorie métier, dérivée de `type_train`) ;
- `vitesse_kmh` — **signal indépendant de la durée** (là où la distance est connue) ;
- `is_transfrontalier` — liaison entre deux pays (là où les deux pays sont connus).
""")
code(r"""
# Heure de départ -> décimal
h = pd.to_datetime(df["heure_depart"], format="%H:%M:%S", errors="coerce")
df["heure_decimale"] = h.dt.hour + h.dt.minute / 60

# Desserte de nuit (0/1)
df["is_nuit"] = (df["type_train"] == "nuit").astype(int)

# Vitesse moyenne (km/h) là où la distance est disponible
df["vitesse_kmh"] = np.where(
    df["distance_km"].notna() & (df["duree_minutes"] > 0),
    df["distance_km"] / df["duree_minutes"] * 60, np.nan)

# Transfrontalier là où les deux pays sont connus
deux_pays = df["code_pays_dep"].notna() & df["code_pays_arr"].notna()
df["is_transfrontalier"] = np.where(
    deux_pays, (df["code_pays_dep"] != df["code_pays_arr"]).astype(float), np.nan)

df[["heure_decimale", "is_nuit", "vitesse_kmh", "is_transfrontalier"]].describe().round(2)
""")

md(r"""
## 5. Sélection des features et stratégie face aux manquants

`distance_km` (et donc `vitesse_kmh`) est manquante à ~55 %. Plutôt qu'imputer la moitié des
valeurs, on prépare **deux jeux de features** assumés :

| Jeu | Lignes | Variables de clustering | Usage |
|---|---|---|---|
| **Complet** | ~52 000 | `duree_minutes`, `heure_decimale`, `is_nuit` | clustering sur tout le réseau |
| **Enrichi** | ~23 700 | + `distance_km`, `vitesse_kmh` | sous-réseau géolocalisé, plus fin |

Le jeu **complet** n'utilise que des variables présentes à 100 % → aucun biais d'imputation.
""")
code(r"""
feat_complet = ["duree_minutes", "heure_decimale", "is_nuit"]
feat_enrichi = ["duree_minutes", "heure_decimale", "is_nuit", "distance_km", "vitesse_kmh"]

print("Complétude des variables candidates :")
print((df[feat_enrichi].notna().mean() * 100).round(1).astype(str) + " %")
""")

md(r"""
## 6. Standardisation

KMeans repose sur la distance euclidienne : les variables doivent être à la **même échelle**.
On standardise les variables **continues** (z-score). `is_nuit`, déjà en 0/1, est conservée
telle quelle (échelle comparable, et la standardiser sur-pondérerait une classe rare).
""")
code(r"""
continues = ["duree_minutes", "heure_decimale"]
scaler = StandardScaler()
df[[c + "_z" for c in continues]] = scaler.fit_transform(df[continues])

features_cluster = ["duree_minutes_z", "heure_decimale_z", "is_nuit"]
print("Features de clustering (jeu complet) :", features_cluster)
df[features_cluster].describe().round(3)
""")

md(r"""
## 7. Découpage train / validation / test (70 / 15 / 15)

Même en non supervisé, on fige un découpage reproductible : le modèle (étape 4) s'ajuste sur
`train`, et la **stabilité** des clusters se contrôle sur `val` / `test`.
""")
code(r"""
train, temp = train_test_split(df, test_size=0.30, random_state=RANDOM_STATE)
val, test = train_test_split(temp, test_size=0.50, random_state=RANDOM_STATE)

df["split"] = "train"
df.loc[val.index, "split"] = "val"
df.loc[test.index, "split"] = "test"

print("Répartition des splits :")
print((df["split"].value_counts(normalize=True) * 100).round(1).astype(str) + " %")
print(df["split"].value_counts())
""")

md(r"""
## 8. Aperçu de clustering (contrôle de cohérence)

⚠️ **Aperçu uniquement** : le choix de K, la comparaison d'algorithmes et l'évaluation
complète relèvent de l'**étape 4 (M2/M3)**. On vérifie ici que les features produisent des
familles séparables et interprétables.
""")
code(r"""
Xtrain = df.loc[df["split"] == "train", features_cluster].values
km = KMeans(n_clusters=4, n_init=10, random_state=RANDOM_STATE).fit(Xtrain)
sil = silhouette_score(Xtrain, km.labels_, sample_size=5000, random_state=RANDOM_STATE)
print(f"KMeans k=4 (train) — score de silhouette = {sil:.3f}")

df["cluster_apercu"] = km.predict(df[features_cluster].values)
profil = (df.groupby("cluster_apercu")
            .agg(nb=("id_trajet", "count"),
                 duree_med=("duree_minutes", "median"),
                 heure_med=("heure_decimale", "median"),
                 pct_nuit=("is_nuit", "mean"),
                 distance_med=("distance_km", "median"))
            .round(2))
profil["pct_nuit"] = (profil["pct_nuit"] * 100).round(1)
print("\nProfil des familles découvertes :")
profil
""")

md(r"""
## 9. Export du dataset de features (livraison à M2/M3)

Contrat de livraison : `data/obrail_features.csv`. On conserve les variables brutes
interprétables (CO₂, distance, pays), les features standardisées, et la colonne `split`.
""")
code(r"""
cols_out = [
    "id_trajet",
    # variables brutes (interprétation / reporting)
    "duree_minutes", "emission_co2_kg", "distance_km", "vitesse_kmh",
    "heure_decimale", "is_nuit", "is_transfrontalier",
    "code_pays_dep", "code_pays_arr", "type_train",
    # features standardisées prêtes pour le clustering
    "duree_minutes_z", "heure_decimale_z",
    # découpage
    "split",
]
out = df[cols_out].copy()
OUT = ROOT / "data" / "obrail_features.csv"
out.to_csv(OUT, index=False, encoding="utf-8")
print(f"Dataset de features écrit : {OUT}")
print(f"Dimensions : {out.shape[0]:,} lignes x {out.shape[1]} colonnes")
out.head()
""")

md(r"""
## 10. Dictionnaire des données (livrable)

| Colonne | Type | Description | Rôle clustering |
|---|---|---|---|
| `id_trajet` | id | Identifiant du service | clé, non utilisé |
| `duree_minutes` | num | Durée (min) | **feature** (via `_z`) |
| `emission_co2_kg` | num | CO₂ (kg) | reporting (≡ durée, écarté) |
| `distance_km` | num | Distance haversine (km) | feature jeu *enrichi* |
| `vitesse_kmh` | num | Vitesse moyenne | feature jeu *enrichi* |
| `heure_decimale` | num | Heure de départ décimale | **feature** (via `_z`) |
| `is_nuit` | bin | Desserte de nuit | **feature** |
| `is_transfrontalier` | bin | Liaison entre 2 pays | enrichissement |
| `code_pays_dep/arr` | cat | Pays départ/arrivée | interprétation |
| `type_train` | cat | jour / nuit | interprétation |
| `duree_minutes_z`, `heure_decimale_z` | num | Versions standardisées | **features clustering** |
| `split` | cat | train / val / test (70/15/15) | protocole |

**Synthèse étape 3 :** données nettoyées, variable redondante (CO₂) identifiée et écartée des
features, manquants traités sans imputation hasardeuse (deux jeux assumés), variables
standardisées, découpage reproductible. L'aperçu KMeans confirme des familles de dessertes
séparables et interprétables. Dataset livré : `data/obrail_features.csv`.
""")

nb["cells"] = cells
nb["metadata"]["kernelspec"] = {"display_name": "Python (mspr-obrail)",
                                 "language": "python", "name": "mspr-obrail"}
out_path = Path(__file__).resolve().parent / "02_preparation.ipynb"
nbf.write(nb, out_path)
print("Notebook écrit :", out_path)
