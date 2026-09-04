"""Evaluate the sticky note generation model."""
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from src.config import DATA_DIR, MODELS_DIR, PLOTS_DIR, REPORTS_DIR

warnings.filterwarnings("ignore")


def evaluate_classifier():
    features_path = DATA_DIR / "extracted_features.csv"
    if not features_path.exists():
        print("No features file found. Run generate_dataset and features first.")
        return None

    df = pd.read_csv(features_path)
    y_true = df["label"].values

    model_path = MODELS_DIR / "important_content_classifier.joblib"
    if not model_path.exists():
        print("No trained model found. Run train_pipeline first.")
        return None

    import joblib
    bundle = joblib.load(model_path)
    model = bundle["model"]
    scaler = bundle.get("scaler")
    feature_cols = bundle["feature_cols"]

    X = df[feature_cols].fillna(0).values
    if scaler is not None and bundle.get("best_model_name") in ("Logistic Regression", "SVM"):
        X = scaler.transform(X)

    y_pred = model.predict(X)

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average="macro", zero_division=0)
    rec = recall_score(y_true, y_pred, average="macro", zero_division=0)
    f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    f1_weighted = f1_score(y_true, y_pred, average="weighted", zero_division=0)

    metrics = {
        "accuracy": round(float(acc), 4),
        "precision_macro": round(float(prec), 4),
        "recall_macro": round(float(rec), 4),
        "f1_macro": round(float(f1), 4),
        "f1_weighted": round(float(f1_weighted), 4),
        "classification_report": classification_report(y_true, y_pred, target_names=["Casual", "Important"]),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "best_model": bundle.get("best_model_name", "unknown"),
        "dataset_size": len(df),
    }

    report_path = REPORTS_DIR / "evaluation_metrics.json"
    with open(report_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"Saved evaluation metrics -> {report_path}")

    cr_path = REPORTS_DIR / "classification_report.txt"
    with open(cr_path, "w") as f:
        f.write(metrics["classification_report"])
    print(f"Saved classification report -> {cr_path}")

    cm = np.array(metrics["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="YlOrRd",
                xticklabels=["Casual", "Important"],
                yticklabels=["Casual", "Important"], ax=ax)
    ax.set_title("Full Dataset Confusion Matrix")
    ax.set_ylabel("True Label")
    ax.set_xlabel("Predicted Label")
    plt.tight_layout()
    fig.savefig(PLOTS_DIR / "04_full_confusion_matrix.png", dpi=150)
    plt.close(fig)

    print(f"\n{'='*50}")
    print(f"FULL DATASET EVALUATION")
    print(f"{'='*50}")
    print(f"Accuracy:       {acc:.4f}")
    print(f"Precision:      {prec:.4f}")
    print(f"Recall:         {rec:.4f}")
    print(f"F1 (macro):     {f1:.4f}")
    print(f"F1 (weighted):  {f1_weighted:.4f}")
    print(f"{'='*50}")

    return metrics


def compute_rouge_scores(predicted: list[str], reference: list[str]) -> dict:
    def _ngrams(text, n):
        words = text.lower().split()
        return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))

    def _rouge_l(pred, ref):
        p_words = pred.lower().split()
        r_words = ref.lower().split()
        m = len(p_words)
        n = len(r_words)
        if m == 0 or n == 0:
            return 0.0
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if p_words[i-1] == r_words[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        lcs_len = dp[m][n]
        precision = lcs_len / m if m > 0 else 0
        recall = lcs_len / n if n > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        return f1

    scores = {"rouge_1": [], "rouge_2": [], "rouge_l": []}
    for pred, ref in zip(predicted, reference):
        p1 = _ngrams(pred, 1)
        r1 = _ngrams(ref, 1)
        inter1 = len(p1 & r1)
        prec1 = inter1 / len(p1) if p1 else 0
        rec1 = inter1 / len(r1) if r1 else 0
        f1_1 = 2 * prec1 * rec1 / (prec1 + rec1) if (prec1 + rec1) > 0 else 0
        scores["rouge_1"].append(f1_1)

        p2 = _ngrams(pred, 2)
        r2 = _ngrams(ref, 2)
        inter2 = len(p2 & r2)
        prec2 = inter2 / len(p2) if p2 else 0
        rec2 = inter2 / len(r2) if r2 else 0
        f1_2 = 2 * prec2 * rec2 / (prec2 + rec2) if (prec2 + rec2) > 0 else 0
        scores["rouge_2"].append(f1_2)

        scores["rouge_l"].append(_rouge_l(pred, ref))

    return {k: round(np.mean(v), 4) for k, v in scores.items()}


def compute_bleu_scores(predicted: list[str], reference: list[str]) -> dict:
    def _bleu(pred, ref, max_n=4):
        pred_words = pred.lower().split()
        ref_words = ref.lower().split()
        scores = []
        for n in range(1, max_n + 1):
            pred_ngrams = [tuple(pred_words[i:i+n]) for i in range(len(pred_words) - n + 1)]
            ref_ngrams = set(tuple(ref_words[i:i+n]) for i in range(len(ref_words) - n + 1))
            if not pred_ngrams:
                scores.append(0.0)
                continue
            matches = sum(1 for ng in pred_ngrams if ng in ref_ngrams)
            scores.append(matches / len(pred_ngrams))
        if any(s == 0 for s in scores):
            return 0.0
        geometric_mean = np.exp(np.mean([np.log(s) for s in scores]))
        bp = min(1.0, np.exp(1 - len(ref_words) / max(1, len(pred_words))))
        return bp * geometric_mean

    return {"bleu": round(np.mean([_bleu(p, r) for p, r in zip(predicted, reference)]), 4)}


def compute_meteor_scores(predicted: list[str], reference: list[str]) -> dict:
    def _meteor_single(pred, ref):
        pred_words = pred.lower().split()
        ref_words = ref.lower().split()
        matches = sum(1 for w in pred_words if w in ref_words)
        precision = matches / len(pred_words) if pred_words else 0
        recall = matches / len(ref_words) if ref_words else 0
        if precision + recall == 0:
            return 0.0
        return (precision * recall) / (0.7 * precision + 0.3 * recall)

    scores = [_meteor_single(p, r) for p, r in zip(predicted, reference)]
    return {"meteor": round(np.mean(scores), 4)}


def evaluate_summary_quality(predicted_notes: list[str], reference_notes: list[str]) -> dict:
    rouge = compute_rouge_scores(predicted_notes, reference_notes)
    bleu = compute_bleu_scores(predicted_notes, reference_notes)
    meteor = compute_meteor_scores(predicted_notes, reference_notes)

    all_scores = {**rouge, **bleu, **meteor}

    report_path = REPORTS_DIR / "summary_evaluation.json"
    with open(report_path, "w") as f:
        json.dump(all_scores, f, indent=2)
    print(f"Saved summary evaluation -> {report_path}")
    print(f"ROUGE scores: {rouge}")
    print(f"BLEU score: {bleu}")
    print(f"METEOR score: {meteor}")

    return all_scores


if __name__ == "__main__":
    evaluate_classifier()