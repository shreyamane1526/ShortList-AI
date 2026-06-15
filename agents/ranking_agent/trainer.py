from __future__ import annotations

import pandas as pd
import joblib

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


MODEL_PATH = (
    "agents/ranking_agent/"
    "models/xgb_model.pkl"
)


def train_model():

    df = pd.read_csv(
        "agents/ranking_agent/data/training_data.csv"
    )

    X = df.drop(
        columns=["hired"]
    )

    y = df["hired"]

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
        )
    )

    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective="binary:logistic",
    )

    model.fit(
        X_train,
        y_train,
    )

    preds = model.predict(
        X_test
    )

    acc = accuracy_score(
        y_test,
        preds,
    )

    print(
        f"Accuracy: {acc:.4f}"
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    print(
        f"Saved model → {MODEL_PATH}"
    )


if __name__ == "__main__":
    train_model()