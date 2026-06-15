"""
Training data persistence layer.

Stores features + outcomes for
continuous retraining.
"""

from __future__ import annotations

import json
from datetime import datetime

from core.database import get_connection


def save_training_example(
    candidate_id: str,
    features: dict,
    prediction: dict,
    insight: dict,
):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS
        training_examples (

            id SERIAL PRIMARY KEY,

            candidate_id TEXT,

            created_at TIMESTAMP,

            features JSONB,

            prediction JSONB,

            insight JSONB
        )
        """
    )

    cur.execute(
        """
        INSERT INTO training_examples (

            candidate_id,
            created_at,
            features,
            prediction,
            insight

        )

        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            candidate_id,
            datetime.utcnow(),
            json.dumps(features, default=str),
            json.dumps(prediction, default=str),
            json.dumps(insight, default=str),
        ),
    )

    conn.commit()

    cur.close()

    conn.close()

    print(
        "[training_repository] "
        "training example stored"
    )