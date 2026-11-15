# backend/ml_predictor.py
import json
import math
import pickle
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

FEATURE_COLS = [
    "elo_diff",
    "pace_wicket_pct",
    "spin_wicket_pct",
    "avg_first_innings_score",
    "historical_draw_pct",
]

CLASS_LABELS = ["HOME_WIN", "DRAW", "AWAY_WIN"]


def generate_historical_training_corpus() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n_samples = 400

    elo_diffs = rng.normal(loc=20.0, scale=120.0, size=n_samples)
    pace_pcts = rng.uniform(25.0, 85.0, size=n_samples)
    spin_pcts = 100.0 - pace_pcts
    first_inn_scores = rng.normal(loc=325.0, scale=45.0, size=n_samples)
    hist_draw_pcts = rng.uniform(10.0, 30.0, size=n_samples)

    labels = []
    for i in range(n_samples):
        ed = elo_diffs[i]
        draw_hist = hist_draw_pcts[i]
        score = first_inn_scores[i]

        p_home_base = 0.40 + (ed / 600.0)
        p_draw_base = 0.18 + (draw_hist / 100.0) * 0.35 + (max(0, score - 330) / 1000.0)
        p_away_base = 0.42 - (ed / 600.0)

        raw_probs = np.array([max(0.08, p_home_base), max(0.08, p_draw_base), max(0.08, p_away_base)])
        norm_probs = raw_probs / raw_probs.sum()

        chosen_outcome = rng.choice([0, 1, 2], p=norm_probs)
        labels.append(chosen_outcome)

    df_train = pd.DataFrame({
        "elo_diff": elo_diffs,
        "pace_wicket_pct": pace_pcts,
        "spin_wicket_pct": spin_pcts,
        "avg_first_innings_score": first_inn_scores,
        "historical_draw_pct": hist_draw_pcts,
        "label": labels,
    })
    return df_train


class WTCModelTrainer:
    def __init__(self):
        self.scaler = StandardScaler()
        base_model = LogisticRegression(solver="lbfgs", max_iter=1000)
        self.calibrated_model = CalibratedClassifierCV(estimator=base_model, cv=5)

    def train_and_save(self) -> None:
        df_train = generate_historical_training_corpus()
        X = df_train[FEATURE_COLS].values
        y = df_train["label"].values

        X_scaled = self.scaler.fit_transform(X)
        self.calibrated_model.fit(X_scaled, y)

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_payload = {
            "scaler": self.scaler,
            "model": self.calibrated_model,
            "feature_cols": FEATURE_COLS,
            "classes": CLASS_LABELS,
        }
        with open(MODELS_DIR / "wtc_model.pkl", "wb") as f:
            pickle.dump(model_payload, f)


class WTCPredictor:
    def __init__(self):
        model_path = MODELS_DIR / "wtc_model.pkl"
        if not model_path.exists():
            trainer = WTCModelTrainer()
            trainer.train_and_save()

        with open(model_path, "rb") as f:
            payload = pickle.load(f)
            self.scaler: StandardScaler = payload["scaler"]
            self.model: CalibratedClassifierCV = payload["model"]
            self.feature_cols: List[str] = payload["feature_cols"]

    def _extract_insights(self, row: pd.Series) -> List[str]:
        insights = []
        elo_diff = row["elo_diff"]
        hist_draw = row["historical_draw_pct"]
        spin_pct = row["spin_wicket_pct"]
        pace_pct = row["pace_wicket_pct"]

        if elo_diff > 50:
            insights.append(f"Home condition Elo advantage (+{elo_diff:.0f} pts) favors {row['home_team']}.")
        elif elo_diff < -50:
            insights.append(f"Visiting team holds a decisive condition-adjusted Elo rating advantage ({row['away_team']} {abs(elo_diff):.0f} pts higher).")
        else:
            insights.append("Evenly matched sides based on current format ratings and conditions.")

        if hist_draw >= 22.0:
            insights.append(f"Elevated draw risk: Ground carries a {hist_draw:.1f}% historical draw rate.")
        elif hist_draw <= 14.0:
            insights.append(f"Decisive pitch: Low draw precedent ({hist_draw:.1f}%) favors a clear result.")

        if spin_pct > 50.0:
            insights.append(f"Spin-dominant venue: Slow bowlers claim {spin_pct:.1f}% of wickets here.")
        elif pace_pct > 75.0:
            insights.append(f"Pace-heavy conditions: Fast bowlers take {pace_pct:.1f}% of dismissals at this ground.")

        return insights

    def predict_upcoming_fixtures(self) -> List[Dict[str, Any]]:
        features_file = DATA_DIR / "engineered_features.json"
        with open(features_file, "r", encoding="utf-8") as f:
            matches = json.load(f)

        df = pd.DataFrame(matches)
        results = []

        for _, row in df.iterrows():
            item = row.to_dict()

            # Clean all float NaN values into Python None (valid JSON null)
            for k, v in list(item.items()):
                if isinstance(v, float) and math.isnan(v):
                    item[k] = None

            if row["status"] == "completed":
                item["prob_home_win"] = 1.0 if row["outcome"] == "HOME_WIN" else 0.0
                item["prob_draw"] = 1.0 if row["outcome"] == "DRAW" else 0.0
                item["prob_away_win"] = 1.0 if row["outcome"] == "AWAY_WIN" else 0.0
                item["insights"] = [f"Match completed: {str(row['outcome']).replace('_', ' ')}"]
            else:
                x_vec = np.array([[row[col] for col in self.feature_cols]])
                x_scaled = self.scaler.transform(x_vec)
                probs = self.model.predict_proba(x_scaled)[0]

                p_home = round(float(probs[0]), 3)
                p_draw = round(float(probs[1]), 3)
                p_away = round(float(probs[2]), 3)

                remainder = round(1.0 - (p_home + p_draw + p_away), 3)
                p_draw = round(p_draw + remainder, 3)

                item["prob_home_win"] = p_home
                item["prob_draw"] = p_draw
                item["prob_away_win"] = p_away
                item["insights"] = self._extract_insights(row)

            results.append(item)

        out_file = DATA_DIR / "fixtures_with_predictions.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        return results


if __name__ == "__main__":
    trainer = WTCModelTrainer()
    trainer.train_and_save()
    predictor = WTCPredictor()
    predictor.predict_upcoming_fixtures()
    print("Predictions regenerated with clean JSON-compliant nulls.")