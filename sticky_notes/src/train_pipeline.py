"""Train models to classify important meeting segments."""
import json
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from src.config import DATA_DIR, MODELS_DIR, PLOTS_DIR, RANDOM_STATE, TEST_SIZE

warnings.filterwarnings("ignore")

FEATURE_COLS = [
    "word_count", "sentence_count", "avg_word_length",
    "has_question", "has_action_verb", "has_decision",
    "contains_date_or_deadline", "keyword_density_action",
    "keyword_density_stopword", "ne_person", "ne_date",
    "ne_time", "ne_email", "positive_words", "negative_words",
    "speaker_same_as_prev", "is_short_utterance",
    "exclamation_count", "caps_ratio",
]


def load_data() -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(DATA_DIR / "extracted_features.csv")
    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0
    X = df[FEATURE_COLS].fillna(0)
    y = df["label"]
    return X, y


def train_and_evaluate() -> dict:
    X, y = load_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, random_state=RANDOM_STATE),
        "SVM": SVC(kernel="rbf", probability=True, random_state=RANDOM_STATE),
    }

    results = {}
    best_f1 = -1
    best_name = None

    for name, model in models.items():
        if name in ("Logistic Regression", "SVM"):
            model.fit(X_train_s, y_train)
            preds = model.predict(X_test_s)
            cv = cross_val_score(model, X_train_s, y_train, cv=5, scoring="f1_macro")
        else:
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            cv = cross_val_score(model, X_train, y_train, cv=5, scoring="f1_macro")

        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, average="macro", zero_division=0)
        rec = recall_score(y_test, preds, average="macro", zero_division=0)
        f1 = f1_score(y_test, preds, average="macro", zero_division=0)

        results[name] = {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_macro": round(float(f1), 4),
            "cv_f1_mean": round(float(cv.mean()), 4),
            "cv_f1_std": round(float(cv.std()), 4),
            "classification_report": classification_report(y_test, preds, target_names=["Casual", "Important"]),
            "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
            "model": model,
        }

        if f1 > best_f1:
            best_f1 = f1
            best_name = name

        print(f"{name}: Acc={acc:.4f}  P={prec:.4f}  R={rec:.4f}  F1={f1:.4f}  CV={cv.mean():.4f}+/-{cv.std():.4f}")

    return {"results": results, "best_model": best_name, "scaler": scaler, "feature_cols": FEATURE_COLS}


def save_models(bundle: dict):
    best_name = bundle["best_model"]
    best_model = bundle["results"][best_name]["model"]

    model_path = MODELS_DIR / "important_content_classifier.joblib"
    joblib.dump({
        "model": best_model,
        "scaler": bundle["scaler"],
        "feature_cols": bundle["feature_cols"],
        "best_model_name": best_name,
    }, model_path)
    print(f"Saved best model ({best_name}) -> {model_path}")

    report = {}
    for name, res in bundle["results"].items():
        report[name] = {
            k: v for k, v in res.items() if k not in ("model",)
        }
    report_path = MODELS_DIR / "model_comparison.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Saved comparison report -> {report_path}")


def plot_results(bundle: dict):
    results = bundle["results"]

    model_names = list(results.keys())
    metrics = ["accuracy", "precision", "recall", "f1_macro"]
    data = []
    for name in model_names:
        for m in metrics:
            data.append({"Model": name, "Metric": m.replace("_", " ").title(), "Score": results[name][m]})

    df = pd.DataFrame(data)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=df, x="Model", y="Score", hue="Metric", palette="Set2", ax=ax)
    ax.set_ylim(0, 1.05)
    ax.set_title("Model Comparison — Important Content Classification", fontsize=13)
    ax.legend(loc="lower right")
    plt.tight_layout()
    fig.savefig(PLOTS_DIR / "01_model_comparison.png", dpi=150)
    plt.close(fig)

    best_name = bundle["best_model"]
    cm = np.array(results[best_name]["confusion_matrix"])
    fig2, ax2 = plt.subplots(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=["Casual", "Important"],
                yticklabels=["Casual", "Important"], ax=ax2)
    ax2.set_title(f"Confusion Matrix — {best_name}")
    ax2.set_ylabel("True")
    ax2.set_xlabel("Predicted")
    plt.tight_layout()
    fig2.savefig(PLOTS_DIR / "02_confusion_matrix.png", dpi=150)
    plt.close(fig2)

    model_obj = results[best_name]["model"]
    importances = None
    if hasattr(model_obj, "feature_importances_"):
        importances = model_obj.feature_importances_
    elif hasattr(model_obj, "coef_"):
        importances = np.abs(model_obj.coef_[0])
    if importances is not None:
        fi_df = pd.DataFrame({"Feature": bundle["feature_cols"], "Importance": importances}).sort_values("Importance", ascending=True)
        fig3, ax3 = plt.subplots(figsize=(8, 6))
        ax3.barh(fi_df["Feature"], fi_df["Importance"], color=sns.color_palette("viridis", len(fi_df)))
        ax3.set_title(f"Feature Importance — {best_name}")
        plt.tight_layout()
        fig3.savefig(PLOTS_DIR / "03_feature_importance.png", dpi=150)
        plt.close(fig3)

    print(f"Plots saved to {PLOTS_DIR}")


def run_training():
    print("=" * 60)
    print("Training Important Content Classifier")
    print("=" * 60)
    bundle = train_and_evaluate()
    save_models(bundle)
    plot_results(bundle)
    print("Training complete!")
    return bundle


if __name__ == "__main__":
    run_training()