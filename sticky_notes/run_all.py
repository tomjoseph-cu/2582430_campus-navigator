"""Run the full pipeline: generate data, extract features, train, evaluate, report."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.generate_dataset import save_dataset
from src.features import build_feature_dataframe
from src.train_pipeline import run_training
from src.evaluate import evaluate_classifier
from src.generate_report import generate_report
from src.config import DATA_DIR


def run_all():
    print("=" * 60)
    print("STICKY NOTE GENERATION — FULL PIPELINE")
    print("=" * 60)

    print("\n[1/5] Generating dataset...")
    save_dataset()

    print("\n[2/5] Extracting features...")
    build_feature_dataframe()

    print("\n[3/5] Training models...")
    run_training()

    print("\n[4/5] Evaluating performance...")
    evaluate_classifier()

    print("\n[5/5] Generating report...")
    generate_report()

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Dataset:    {DATA_DIR}")
    print(f"Models:     {DATA_DIR.parent / 'outputs' / 'models'}")
    print(f"Plots:      {DATA_DIR.parent / 'outputs' / 'plots'}")
    print(f"Reports:    {DATA_DIR.parent / 'outputs' / 'reports'}")
    print("\nRun the UI with: streamlit run app.py")


if __name__ == "__main__":
    run_all()