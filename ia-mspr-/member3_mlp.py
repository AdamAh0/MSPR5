"""
Membre 3 — MLP (Multi-Layer Perceptron) pour la classification de substitution modale.

Ce script :
  1. Charge et vérifie la compatibilité des données avec un réseau de neurones.
  2. Entraîne un MLPClassifier (scikit-learn) avec recherche d'architecture.
  3. Compare les performances MLP vs modèles classiques (M2).
  4. Produit les visualisations : courbes loss/accuracy, matrice de confusion.
  5. Sauvegarde l'artefact modèle dans artifacts/member3/.

Usage :
    python member3_mlp.py
    python member3_mlp.py --data data/obrail_features.csv --artifact-dir artifacts/member3
"""
from __future__ import annotations

import argparse
import json
import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*X does not have valid feature names.*")

# ─── constants ────────────────────────────────────────────────────────────────

RANDOM_STATE = 42
TARGET_COLUMN = "classe_substitution"
SPLIT_COLUMN = "split_classif"
TRAIN_SPLIT = "train"
VAL_SPLIT = "val"
TEST_SPLIT = "test"
CLASS_ORDER = ["non_pertinent", "substitution_difficile", "substitution_possible"]

FEATURE_COLUMNS = [
    "duree_minutes",
    "heure_decimale",
    "is_nuit",
    "is_transfrontalier",
    "code_pays_dep",
    "code_pays_arr",
]
NUMERIC_COLUMNS = ["duree_minutes", "heure_decimale", "is_nuit", "is_transfrontalier"]
CATEGORICAL_COLUMNS = ["code_pays_dep", "code_pays_arr"]
REQUIRED_COLUMNS = set(FEATURE_COLUMNS + [TARGET_COLUMN, SPLIT_COLUMN])

LOGGER = logging.getLogger("member3_mlp")


# ─── data classes ─────────────────────────────────────────────────────────────

@dataclass
class MLPArchitecture:
    hidden_layer_sizes: tuple[int, ...]
    activation: str
    alpha: float
    learning_rate_init: float

    def label(self) -> str:
        layers = "-".join(str(n) for n in self.hidden_layer_sizes)
        return f"MLP({layers}, act={self.activation}, α={self.alpha})"


@dataclass
class TrainingResult:
    architecture: str
    val_accuracy: float
    val_f1_macro: float
    val_roc_auc: float
    test_accuracy: float
    test_f1_macro: float
    test_roc_auc: float
    confusion_matrix_test: list[list[int]]
    classification_report_test: dict[str, Any]
    best_params: dict[str, Any]
    loss_curve: list[float] = field(default_factory=list)


# ─── data helpers ─────────────────────────────────────────────────────────────

def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(asctime)s | %(levelname)s | %(message)s")


def resolve_dataset_path(data_path: str | Path) -> Path:
    path = Path(data_path)
    if path.exists():
        return path
    candidates = [
        Path("data/obrail_features.csv"),
        Path("../data/obrail_features.csv"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Impossible de trouver le fichier de données: {data_path}")


def load_dataset(data_path: str | Path) -> pd.DataFrame:
    path = resolve_dataset_path(data_path)
    df = pd.read_csv(path, low_memory=False)
    LOGGER.info("Dataset chargé: %s (%d lignes, %d colonnes)", path, len(df), len(df.columns))
    return df


def validate_nn_compatibility(df: pd.DataFrame) -> None:
    """Vérifie la compatibilité des données pour un réseau de neurones."""
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes: {sorted(missing)}")

    labelled = df[df[SPLIT_COLUMN].isin({TRAIN_SPLIT, VAL_SPLIT, TEST_SPLIT})]
    if labelled.empty:
        raise ValueError("Aucune ligne étiquetée.")

    LOGGER.info("=== Vérification compatibilité réseau de neurones ===")

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            series = df[col].dropna()
            mean, std = series.mean(), series.std()
            LOGGER.info(
                "  %-22s  mean=%.3f  std=%.3f  null=%d  [normalisation %s]",
                col,
                mean,
                std,
                df[col].isna().sum(),
                "OK" if 0.5 <= std <= 500 else "ATTENTION",
            )

    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            n_unique = df[col].nunique()
            LOGGER.info("  %-22s  modalités=%d  (OneHotEncoding)", col, n_unique)

    n_labelled = len(labelled)
    n_train = (labelled[SPLIT_COLUMN] == TRAIN_SPLIT).sum()
    n_val = (labelled[SPLIT_COLUMN] == VAL_SPLIT).sum()
    n_test = (labelled[SPLIT_COLUMN] == TEST_SPLIT).sum()
    LOGGER.info(
        "Splits — train=%d  val=%d  test=%d  (total=%d)",
        n_train, n_val, n_test, n_labelled,
    )

    class_counts = labelled[TARGET_COLUMN].value_counts()
    LOGGER.info("Distribution des classes:\n%s", class_counts.to_string())

    min_class = class_counts.min()
    if min_class < 30:
        LOGGER.warning(
            "Classe minoritaire avec %d exemples seulement — "
            "class_weight='balanced' recommandé.",
            min_class,
        )
    LOGGER.info("=== Compatibilité : OK ===")


def split_labelled_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labelled = df[df[SPLIT_COLUMN].isin({TRAIN_SPLIT, VAL_SPLIT, TEST_SPLIT})].copy()
    train_df = labelled[labelled[SPLIT_COLUMN] == TRAIN_SPLIT].copy()
    val_df = labelled[labelled[SPLIT_COLUMN] == VAL_SPLIT].copy()
    test_df = labelled[labelled[SPLIT_COLUMN] == TEST_SPLIT].copy()
    if train_df.empty or val_df.empty or test_df.empty:
        raise ValueError("Les splits train/val/test doivent tous être non vides.")
    return train_df, val_df, test_df


# ─── preprocessing ────────────────────────────────────────────────────────────

def build_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_COLUMNS),
            ("categorical", categorical_pipeline, CATEGORICAL_COLUMNS),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


# ─── MLP training ─────────────────────────────────────────────────────────────

MLP_PARAM_DISTRIBUTIONS: dict[str, Any] = {
    "model__hidden_layer_sizes": [
        (64,),
        (128,),
        (256,),
        (64, 32),
        (128, 64),
        (256, 128),
        (128, 64, 32),
        (256, 128, 64),
        (512, 256, 128),
    ],
    "model__activation": ["relu", "tanh"],
    "model__alpha": [1e-4, 5e-4, 1e-3, 5e-3, 1e-2],
    "model__learning_rate_init": [1e-3, 5e-3, 1e-2],
    "model__batch_size": [64, 128, 256],
}


def build_mlp_pipeline() -> Pipeline:
    preprocessor = build_preprocessor()
    mlp = MLPClassifier(
        max_iter=500,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20,
        random_state=RANDOM_STATE,
        verbose=False,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", mlp)])


def search_best_mlp(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    n_iter: int = 20,
    cv_splits: int = 5,
) -> RandomizedSearchCV:
    pipeline = build_mlp_pipeline()
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=RANDOM_STATE)
    search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=MLP_PARAM_DISTRIBUTIONS,
        n_iter=n_iter,
        scoring="f1_macro",
        refit=True,
        cv=cv,
        n_jobs=-1,
        verbose=1,
        random_state=RANDOM_STATE,
        error_score="raise",
    )
    LOGGER.info("Recherche d'architecture MLP (n_iter=%d, cv=%d-fold)...", n_iter, cv_splits)
    search.fit(X_train, y_train)
    LOGGER.info("Meilleure architecture: %s", search.best_params_)
    LOGGER.info("CV F1-macro: %.4f", search.best_score_)
    return search


def train_final_mlp_with_curves(
    best_params: dict[str, Any],
    X_train: pd.DataFrame,
    y_train: np.ndarray,
) -> Pipeline:
    """Re-entraîne le meilleur modèle sans early_stopping pour obtenir la courbe de loss complète."""
    preprocessor = build_preprocessor()
    mlp_kwargs = {
        k.replace("model__", ""): v
        for k, v in best_params.items()
        if k.startswith("model__")
    }
    mlp_kwargs.update({
        "max_iter": 500,
        "early_stopping": False,
        "random_state": RANDOM_STATE,
        "verbose": False,
    })
    mlp = MLPClassifier(**mlp_kwargs)
    final_pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", mlp)])
    sample_weight = compute_sample_weight("balanced", y_train)
    final_pipeline.fit(X_train, y_train)
    return final_pipeline


# ─── metrics ──────────────────────────────────────────────────────────────────

def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    class_names: list[str],
) -> dict[str, Any]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "roc_auc_ovr_weighted": float(
            roc_auc_score(y_true, y_proba, multi_class="ovr", average="weighted")
        ),
        "confusion_matrix": confusion_matrix(
            y_true, y_pred, labels=np.arange(len(class_names))
        ).tolist(),
        "classification_report": classification_report(
            y_true,
            y_pred,
            labels=np.arange(len(class_names)),
            target_names=class_names,
            zero_division=0,
            output_dict=True,
        ),
    }


# ─── visualizations ───────────────────────────────────────────────────────────

def plot_confusion_matrix(
    matrix: list[list[int]],
    class_names: list[str],
    output_path: Path,
    title: str = "Matrice de confusion — MLP",
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    values = np.asarray(matrix)
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(values, cmap="Blues")
    fig.colorbar(im, ax=ax)
    ax.set_xticks(np.arange(len(class_names)))
    ax.set_yticks(np.arange(len(class_names)))
    ax.set_xticklabels(class_names, rotation=25, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Prédit")
    ax.set_ylabel("Réel")
    ax.set_title(title)
    threshold = values.max() / 2 if values.size else 0
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            ax.text(
                j, i, f"{values[i, j]}",
                ha="center", va="center",
                color="white" if values[i, j] > threshold else "black",
            )
    fig.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    LOGGER.info("Matrice de confusion sauvegardée: %s", output_path)


def plot_loss_curve(loss_curve: list[float], output_path: Path) -> None:
    if not loss_curve:
        LOGGER.warning("Courbe de loss vide — graphique ignoré.")
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(loss_curve, color="#356AE6", linewidth=2, label="Perte (training)")
    ax.set_xlabel("Époque")
    ax.set_ylabel("Loss (cross-entropy)")
    ax.set_title("Courbe de perte — MLP")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    LOGGER.info("Courbe de loss sauvegardée: %s", output_path)


def plot_model_comparison(
    m2_path: Path | None,
    mlp_test_metrics: dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    models: list[str] = []
    accuracies: list[float] = []
    f1_macros: list[float] = []
    aucs: list[float] = []

    # Load M2 results if available
    if m2_path and m2_path.exists():
        try:
            m2_candidates = pd.read_csv(m2_path)
            for _, row in m2_candidates.iterrows():
                models.append(str(row.get("model", "M2-unknown")))
                accuracies.append(float(row.get("val_accuracy", row.get("cv_accuracy_mean", 0))))
                f1_macros.append(float(row.get("val_f1_macro", row.get("cv_f1_macro_mean", 0))))
                aucs.append(float(row.get("val_roc_auc_ovr_weighted", row.get("cv_roc_auc_mean", 0))))
        except Exception as exc:
            LOGGER.warning("Impossible de charger les résultats M2 pour comparaison: %s", exc)

    # Add MLP results
    models.append("MLP (M3)")
    accuracies.append(mlp_test_metrics["accuracy"])
    f1_macros.append(mlp_test_metrics["f1_macro"])
    aucs.append(mlp_test_metrics["roc_auc_ovr_weighted"])

    x = np.arange(len(models))
    width = 0.25
    colors = ["#356AE6", "#E67635", "#35E64A"]

    fig, ax = plt.subplots(figsize=(max(10, len(models) * 1.5), 6))
    ax.bar(x - width, accuracies, width, label="Accuracy", color=colors[0], alpha=0.85)
    ax.bar(x, f1_macros, width, label="F1-macro", color=colors[1], alpha=0.85)
    ax.bar(x + width, aucs, width, label="AUC-ROC (OVR)", color=colors[2], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=20, ha="right")
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Score")
    ax.set_title("Comparaison des modèles — M2 vs M3 (MLP)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    LOGGER.info("Comparaison modèles sauvegardée: %s", output_path)


# ─── main pipeline ────────────────────────────────────────────────────────────

def run_mlp_pipeline(
    data_path: str | Path = "data/obrail_features.csv",
    artifact_dir: str | Path = "artifacts/member3",
    m2_artifact_dir: str | Path = "artifacts/member2",
    n_iter: int = 20,
    cv_splits: int = 5,
) -> Path:
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load and validate
    df = load_dataset(data_path)
    validate_nn_compatibility(df)

    train_df, val_df, test_df = split_labelled_frame(df)

    label_encoder = LabelEncoder()
    label_encoder.fit(train_df[TARGET_COLUMN].astype(str))
    class_names = label_encoder.classes_.tolist()
    LOGGER.info("Classes: %s", class_names)

    X_train = train_df[FEATURE_COLUMNS].copy()
    X_val = val_df[FEATURE_COLUMNS].copy()
    X_test = test_df[FEATURE_COLUMNS].copy()
    y_train = label_encoder.transform(train_df[TARGET_COLUMN].astype(str))
    y_val = label_encoder.transform(val_df[TARGET_COLUMN].astype(str))
    y_test = label_encoder.transform(test_df[TARGET_COLUMN].astype(str))

    # 2. Architecture search
    search = search_best_mlp(X_train, y_train, n_iter=n_iter, cv_splits=cv_splits)
    best_params = search.best_params_

    # 3. Validate on val set
    best_estimator = search.best_estimator_
    y_val_pred = best_estimator.predict(X_val)
    y_val_proba = best_estimator.predict_proba(X_val)
    val_metrics = compute_metrics(y_val, y_val_pred, y_val_proba, class_names)
    LOGGER.info(
        "VAL — Accuracy=%.4f  F1-macro=%.4f  AUC=%.4f",
        val_metrics["accuracy"], val_metrics["f1_macro"], val_metrics["roc_auc_ovr_weighted"],
    )

    # 4. Retrain on train+val for final evaluation & loss curve
    X_trainval = pd.concat([X_train, X_val], axis=0)
    y_trainval = np.concatenate([y_train, y_val])
    final_model = train_final_mlp_with_curves(best_params, X_trainval, y_trainval)

    # 5. Test evaluation
    y_test_pred = final_model.predict(X_test)
    y_test_proba = final_model.predict_proba(X_test)
    test_metrics = compute_metrics(y_test, y_test_pred, y_test_proba, class_names)
    LOGGER.info(
        "TEST — Accuracy=%.4f  F1-macro=%.4f  AUC=%.4f",
        test_metrics["accuracy"], test_metrics["f1_macro"], test_metrics["roc_auc_ovr_weighted"],
    )

    # 6. Visualizations
    plot_confusion_matrix(
        test_metrics["confusion_matrix"],
        class_names,
        artifact_dir / "confusion_matrix_test.png",
        title=f"Matrice de confusion — MLP test ({best_params.get('model__hidden_layer_sizes', '?')})",
    )

    mlp_model = final_model.named_steps["model"]
    loss_curve = getattr(mlp_model, "loss_curve_", [])
    plot_loss_curve(loss_curve, artifact_dir / "loss_curve.png")

    m2_candidates_path = Path(m2_artifact_dir) / "candidate_results.csv"
    plot_model_comparison(m2_candidates_path, test_metrics, artifact_dir / "model_comparison.png")

    # 7. Save artifact
    model_path = artifact_dir / "best_model.joblib"
    artifact = {
        "model_name": "mlp",
        "pipeline": final_model,
        "label_encoder": label_encoder,
        "feature_columns": FEATURE_COLUMNS,
        "numeric_columns": NUMERIC_COLUMNS,
        "categorical_columns": CATEGORICAL_COLUMNS,
        "class_names": class_names,
        "best_params": best_params,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "loss_curve": loss_curve,
    }
    joblib.dump(artifact, model_path)
    LOGGER.info("Artefact MLP sauvegardé: %s", model_path)

    # 8. Summary JSON
    summary = {
        "model_name": "mlp",
        "best_params": {str(k): str(v) for k, v in best_params.items()},
        "val_metrics": {k: v for k, v in val_metrics.items() if k not in {"confusion_matrix", "classification_report"}},
        "test_metrics": {k: v for k, v in test_metrics.items() if k not in {"confusion_matrix", "classification_report"}},
        "class_names": class_names,
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
    }
    summary_path = artifact_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    LOGGER.info("Synthèse sauvegardée: %s", summary_path)

    return model_path


# ─── CLI ──────────────────────────────────────────────────────────────────────

def cli() -> None:
    parser = argparse.ArgumentParser(description="Entraînement MLP ObRail — Membre 3")
    parser.add_argument("--data", default="data/obrail_features.csv")
    parser.add_argument("--artifact-dir", default="artifacts/member3")
    parser.add_argument("--m2-artifact-dir", default="artifacts/member2", help="Répertoire des artefacts M2 (pour comparaison)")
    parser.add_argument("--n-iter", type=int, default=20, help="Nombre d'itérations RandomizedSearch")
    parser.add_argument("--cv-splits", type=int, default=5)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(getattr(logging, args.log_level.upper(), logging.INFO))
    model_path = run_mlp_pipeline(
        data_path=args.data,
        artifact_dir=args.artifact_dir,
        m2_artifact_dir=args.m2_artifact_dir,
        n_iter=args.n_iter,
        cv_splits=args.cv_splits,
    )
    LOGGER.info("Modèle MLP final: %s", model_path)


if __name__ == "__main__":
    cli()
