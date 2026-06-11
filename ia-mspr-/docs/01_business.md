# Étape 1 — Business : spécifications fonctionnelles de la solution IA

**MSPR ObRail — Bloc E6.2 « Développer un modèle prédictif d'une solution IA »**
**Membre 1 — Data Analyst / ML Lead**

---

## 1. Contexte et enjeu métier

ObRail est une plateforme d'analyse du transport ferroviaire construite lors de la MSPR
Industrialisation (base PostgreSQL/PostGIS alimentée par ETL, API FastAPI). Elle agrège un
référentiel de **52 314 services ferroviaires** (trajets datés/horodatés) avec, pour chacun,
la durée, les émissions de CO₂, les gares, l'opérateur et la ligne.

L'enjeu de fond est celui du **report modal et de la décarbonation** des mobilités
(Green Deal européen) : mieux connaître l'offre ferroviaire pour la rendre plus lisible,
identifier les dessertes fragiles ou atypiques, et appuyer les décisions de planification.

## 2. De l'axe initial à l'axe retenu (justification par la donnée)

L'équipe avait d'abord envisagé un axe **« identification des lignes candidates à la
substitution avion → train »**. L'analyse exploratoire (étape 2) montre, **chiffres à l'appui**,
que cet axe n'est **pas soutenable sur ce jeu de données** :

| Constat (EDA) | Valeur | Conséquence |
|---|---|---|
| Distance médiane | **74 km** | Réseau de courte distance |
| Trajets ≥ 500 km | **624 (1,2 %)** | Cible substitution quasi inexistante |
| Trajets ≥ 800 km | **41 (0,08 %)** | Aucune base d'apprentissage crédible |
| Type de trains | TER, navettes TGV | Offre **régionale**, pas longue distance |
| `distance_km` manquante | **54,7 %** | Variable de la « cible » partiellement absente |
| Jointure `operateur` | **~100 % nulle** | Variable explicative inutilisable en l'état |

> Construire un classifieur « substitution possible / difficile / non pertinent » sur ces
> données reviendrait à (a) apprendre sur une classe quasi vide et (b) **re-prédire une règle
> de seuil distance/durée fabriquée à la main** (circularité méthodologique). Le jury le
> verrait immédiatement.

**Axe retenu : découverte automatique de familles de dessertes ferroviaires (clustering non
supervisé).** Reformulation de la problématique :

> *« Peut-on découvrir automatiquement, sans étiquette préalable, des familles homogènes de
> dessertes ferroviaires (régionales denses, longue distance de nuit, etc.) afin de
> caractériser l'offre et de repérer les liaisons atypiques ? »*

Cet axe : (1) **colle aux données réellement disponibles**, (2) **évite la circularité** des
labels fabriqués, (3) répond à un besoin explicite du cas d'usage (caractériser les dessertes,
détecter les zones fragiles), et (4) correspond au **type d'approche illustré en cours**
(découverte de structure sans genre connu).

## 3. Type de problème d'IA

| Critère | Choix | Justification |
|---|---|---|
| Famille | **Apprentissage non supervisé** (axe principal) | Pas de variable cible fiable ; on cherche une *structure* |
| Tâche | **Partitionnement (clustering)** | Regrouper des services similaires en familles homogènes |
| Algorithmes pressentis (étape 4, M2/M3) | KMeans, clustering hiérarchique | Standards, interprétables, adaptés à des features numériques |
| Classification supervisée | **Livrable complémentaire encadré, cf. §8** | Cible *synthétique* assumée + garde-fous anti-circularité (exclusion `distance_km`/`vitesse_kmh`) |

## 4. Spécifications fonctionnelles du modèle

### 4.1 Entrées (variables candidates)

| Variable | Type | Rôle | Remarque |
|---|---|---|---|
| `duree_minutes` | numérique | structurante | variable la plus complète et fiable |
| `distance_km` | numérique | structurante | haversine ; ~55 % manquante → imputation/filtre documenté |
| `emission_co2_kg` | numérique | structurante | corrigée des valeurs négatives |
| `heure_depart` → heure décimale | numérique | dérivée | rythme de la desserte |
| `type_train` (jour/nuit) | binaire | catégorielle | dérivé de l'heure |
| `code_pays_dep` / `code_pays_arr` | catégorielle | encodée | national vs transfrontalier |
| `operateur` | catégorielle | **écartée** | jointure cassée (~100 % nulle) |
| `nom_ligne`, `id_trajet` | identifiants | **écartés** | non prédictifs |

### 4.2 Sortie attendue

- Une **partition des dessertes en K familles** (K déterminé par la méthode du coude /
  score de silhouette à l'étape 4).
- Pour chaque famille : un **profil interprétable** (durée médiane, distance, % de nuit,
  intensité CO₂, caractère national/transfrontalier).
- Optionnel : un **score d'atypicité** (distance au centre du cluster) pour repérer les
  liaisons hors-norme.

### 4.3 Critères de succès

- **Quantitatif** : score de silhouette acceptable, clusters de taille non dégénérée.
- **Qualitatif (déterminant ici)** : les familles obtenues doivent être **explicables
  métier** (« régional dense », « longue distance de nuit »…). Un cluster qu'on ne sait pas
  nommer n'a pas de valeur opérationnelle.

## 5. Données, limites et grain

- **Grain** : la ligne du dataset est un **service horaire daté**, pas une liaison
  origine-destination unique (52 314 services pour ~3 800 liaisons distinctes). Décision de
  préparation : travailler au niveau service, avec possibilité d'agréger au niveau liaison.
- **Limites assumées** (livrable de transparence) : `distance_km` manquante à 55 %,
  `operateur` inexploitable, gares manquantes ~47 %, quelques CO₂ négatifs / durées nulles
  (nettoyés à l'étape 3).

## 6. Contraintes transverses

- **Reproductibilité** : environnement figé (`requirements.txt`), `random_state` fixé,
  notebooks ré-exécutables de bout en bout.
- **Éthique / RGPD** : données d'offre de transport agrégées, **aucune donnée personnelle**.
- **Interface avec l'équipe** : la sortie de l'étape 3 (`data/obrail_features.csv`) est le
  contrat de livraison vers M2/M3 (modélisation/évaluation).

## 7. Livrables de la partie Membre 1

1. **Étape 1 — Business** : ce document (specs + justification de l'axe).
2. **Étape 2 — Analyse** : `notebooks/01_eda.ipynb` + tableau des variables retenues.
3. **Étape 3 — Préparation** : `notebooks/02_preparation.ipynb` + dataset de features
   documenté, prêt pour le clustering.
4. **Étape 3b — Cible supervisée** : `notebooks/02b_cible_substitution.ipynb` qui ajoute
   la cible `classe_substitution` et le découpage `split_classif` au dataset de features
   (cf. §8).

## 8. Cible supervisée encadrée (livrable de classification M2/M3)

Le clustering (§2 à §4) **reste l'axe d'analyse principal et le plus honnête** au regard
des données. Toutefois, le livrable impose **une tâche supervisée** (M2/M3 doivent
entraîner régression logistique, RandomForest, XGBoost, LightGBM). Nous construisons donc,
**en complément**, une cible de classification, en assumant explicitement ses limites et en
neutralisant la circularité dénoncée au §2.

### 8.1 Définition de la cible `classe_substitution`

Cible **synthétique** (créée par règle, non observée) à 3 classes, fondée sur la distance,
proxy de la **compétitivité de l'aérien** sur le corridor :

| Classe | Règle | Effectif | Justification métier du seuil |
|---|---|---|---|
| `non_pertinent` | distance < **300 km** | 20 835 | En deçà, l'aérien intérieur n'a quasi pas d'offre (le temps d'accès aéroportuaire annule le gain) ; le train est déjà dominant → la substitution n'est pas un enjeu. |
| `substitution_difficile` | 300 ≤ distance < **500 km** | 2 228 | Zone de bascule : selon que le service est un TGV ou un TER, l'avion peut ou non rester compétitif → cas intermédiaire incertain. |
| `substitution_possible` | distance ≥ **500 km** | 624 | Corridors où le court-courrier intérieur est traditionnellement présent et où le report modal est l'enjeu central : **règle empirique des ~3 h de trajet** ferroviaire au-delà desquelles l'avion regagne des parts, **loi française 2023** interdisant les vols intérieurs doublés d'un train < 2 h 30, objectifs du **Green Deal**. |

Le seuil de **500 km** est volontairement conservateur : il isole une classe « substitution
possible » crédible plutôt que de gonfler artificiellement les effectifs. Une **cible binaire**
(`substitution_possible` vs reste) se dérive trivialement de cette colonne si M2 le souhaite.

### 8.2 Limites assumées (transparence pour le jury)

- **Cible synthétique** : aucune substitution n'est *observée*, elle est *fabriquée* par seuil.
- **Aucune donnée avion** : la distance n'est qu'un proxy de « un vol concurrent pourrait
  exister », pas une mesure de substitution réelle.
- **Périmètre réduit** : `distance_km` étant manquante à 54,7 %, seuls **23 687 services
  (45,3 %)** sont étiquetables ; les autres restent `NaN` et hors apprentissage supervisé.
- **Déséquilibre fort** : la classe `substitution_possible` ne pèse que **2,6 %** du périmètre
  étiqueté.

### 8.3 Garde-fous anti-circularité (point méthodologique clé)

Pour ne pas retomber dans la circularité du §2 (« re-prédire une règle de seuil fabriquée à la
main »), les variables explicatives **excluent** :

- **`distance_km`** : c'est la source de la cible (fuite directe).
- **`vitesse_kmh`** : elle vaut exactement `distance_km / duree_minutes × 60` (corrélation
  **1.0**, écart médian nul) ; la conserver permettrait de recomposer la distance.

Les features conservées sont donc des **caractéristiques d'exploitation** : `duree_minutes`,
`emission_co2_kg`, `heure_decimale`, `is_nuit`, `is_transfrontalier`, `code_pays_dep`,
`code_pays_arr`. `duree_minutes` et `emission_co2_kg` sont *corrélées* à la distance (≈ 0.89)
mais **non déterministes** : c'est le signal légitime du modèle, pas une fuite. La question
devient *« peut-on retrouver la bande de distance d'un service à partir de son profil
d'exploitation ? »* — supervisée et non circulaire.

### 8.4 Découpage et évaluation

- **`split_classif`** : découpage **70 / 15 / 15 stratifié** sur la cible (la colonne `split`
  du clustering n'est pas modifiée), garantissant que les 3 classes sont présentes dans
  train (437 « possibles »), val (94) et test (93).
- **Recommandation d'évaluation pour M2** : vu le déséquilibre, privilégier `class_weight=
  'balanced'` (LogReg, RF) / `scale_pos_weight` (XGBoost, LightGBM) et juger en **macro-F1,
  rappel par classe et matrice de confusion**, pas en accuracy globale.
