# backend/data_pipeline.py
import json
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"

# Baseline Test Elo Ratings (Calibrated over historical cycles)
BASE_RATINGS: Dict[str, float] = {
    "AUS": 1780.0,
    "IND": 1765.0,
    "ENG": 1640.0,
    "SA": 1610.0,
    "NZ": 1560.0,
    "PAK": 1490.0,
    "SL": 1450.0,
    "WI": 1380.0,
    "BAN": 1340.0,
}

# Regional condition affinities (Modifier applied to base Elo based on venue condition)
# SENA teams lose efficacy in Subcontinent turners; Subcontinent teams face bounce deficits in SENA.
CONDITION_MODIFIERS: Dict[str, Dict[str, float]] = {
    "SENA": {
        "AUS": +60.0, "ENG": +40.0, "SA": +50.0, "NZ": +50.0,
        "IND": -15.0, "PAK": -50.0, "SL": -70.0, "BAN": -80.0, "WI": -40.0
    },
    "Subcontinent": {
        "IND": +90.0, "PAK": +40.0, "SL": +50.0, "BAN": +30.0,
        "AUS": -35.0, "ENG": -50.0, "SA": -60.0, "NZ": -60.0, "WI": -70.0
    },
    "Caribbean": {
        "WI": +40.0, "IND": +20.0, "AUS": +10.0, "ENG": 0.0,
        "SA": +10.0, "NZ": 0.0, "PAK": +10.0, "SL": -10.0, "BAN": -20.0
    }
}


class WTCDataPipeline:
    def __init__(self):
        self.venue_db = self._load_json(DATA_DIR / "venue_dna.json")
        self.raw_fixtures = self._load_json(DATA_DIR / "fixtures_2025_2027.json")

    @staticmethod
    def _load_json(path: Path) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def compute_effective_elo(self, team: str, condition_type: str, is_home: bool) -> float:
        """
        Calculates an adjusted Elo rating reflecting home advantage and regional familiarity.
        """
        base = BASE_RATINGS.get(team, 1400.0)
        cond_bonus = CONDITION_MODIFIERS.get(condition_type, {}).get(team, 0.0)
        home_advantage = 75.0 if is_home else 0.0
        return base + cond_bonus + home_advantage

    def build_feature_matrix(self) -> pd.DataFrame:
        """
        Transforms fixtures into numeric feature vectors for ML model inference and training.
        """
        rows = []
        for match in self.raw_fixtures:
            venue_info = self.venue_db.get(
                match["venue"],
                {
                    "condition_type": "SENA",
                    "pace_wicket_pct": 65.0,
                    "spin_wicket_pct": 35.0,
                    "avg_first_innings_score": 310,
                    "historical_draw_pct": 18.0
                }
            )

            cond_type = venue_info["condition_type"]
            home_elo = self.compute_effective_elo(match["home_team"], cond_type, is_home=True)
            away_elo = self.compute_effective_elo(match["away_team"], cond_type, is_home=False)

            elo_diff = home_elo - away_elo

            feature_row = {
                "match_id": match["match_id"],
                "series_name": match["series_name"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "venue": match["venue"],
                "status": match["status"],
                "outcome": match.get("outcome"),
                # Core engineered features
                "home_elo": home_elo,
                "away_elo": away_elo,
                "elo_diff": elo_diff,
                "pace_wicket_pct": venue_info["pace_wicket_pct"],
                "spin_wicket_pct": venue_info["spin_wicket_pct"],
                "avg_first_innings_score": venue_info["avg_first_innings_score"],
                "historical_draw_pct": venue_info["historical_draw_pct"],
            }
            rows.append(feature_row)

        df = pd.DataFrame(rows)
        return df


if __name__ == "__main__":
    pipeline = WTCDataPipeline()
    df = pipeline.build_feature_matrix()

    # Save to disk as cached features
    output_path = DATA_DIR / "engineered_features.json"
    df.to_json(output_path, orient="records", indent=2)

    print("\n=== STEP 2: DATA PIPELINE & FEATURE MATRIX BUILT ===")
    print(f"Total fixtures loaded: {len(df)}")
    print(f"Saved feature dataset to: {output_path}")
    print("\nPreview of upcoming match features:")
    preview_cols = ["match_id", "home_team", "away_team", "elo_diff", "pace_wicket_pct", "spin_wicket_pct", "historical_draw_pct"]
    print(df[df["status"] == "upcoming"][preview_cols].to_string(index=False))