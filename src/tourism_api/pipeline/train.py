import json
import os
import time
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = REPO_ROOT / "data" / "india_tourism.csv"
MODEL_DIR = REPO_ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

NUMERIC_FEATURES = ["avg_temp_c", "avg_rainfall_mm", "cost_tier", "month_num"]
CATEGORICAL_FEATURES = ["category", "region"]
TARGET = "suitability_score"

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI")


def train():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run build_dataset.py first."
        )

    if MLFLOW_TRACKING_URI:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("tourism-recommender")

    df = pd.read_csv(DATA_PATH)
    print(f"Loaded dataset: {len(df)} rows, {df['place'].nunique()} places")

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="passthrough",
    )

    model_params = dict(
        n_estimators=300,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", RandomForestRegressor(**model_params)),
        ]
    )

    with mlflow.start_run():
        mlflow.log_params(model_params)
        mlflow.log_param("n_rows", len(df))

        print("Training RandomForestRegressor on suitability_score...")
        start = time.time()
        pipeline.fit(X_train, y_train)
        elapsed = time.time() - start
        print(f"Training finished in {elapsed:.2f}s")

        preds = pipeline.predict(X_test)
        metrics = {
            "mae": float(mean_absolute_error(y_test, preds)),
            "r2": float(r2_score(y_test, preds)),
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
            "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        print("Evaluation metrics:", json.dumps(metrics, indent=2))

        mlflow.log_metric("mae", metrics["mae"])
        mlflow.log_metric("r2", metrics["r2"])
        mlflow.log_metric("training_time_s", elapsed)
        mlflow.sklearn.log_model(pipeline, "model")

        model_path = MODEL_DIR / "tourism_model.joblib"
        joblib.dump(
            {
                "pipeline": pipeline,
                "numeric_features": NUMERIC_FEATURES,
                "categorical_features": CATEGORICAL_FEATURES,
            },
            model_path,
        )
        print(f"Saved trained model to {model_path}")

        with open(MODEL_DIR / "metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)

        df.to_pickle(MODEL_DIR / "lookup_table.pkl")
        print(f"Saved lookup table to {MODEL_DIR / 'lookup_table.pkl'}")

        mlflow.log_artifact(str(MODEL_DIR / "metrics.json"))


if __name__ == "__main__":
    train()