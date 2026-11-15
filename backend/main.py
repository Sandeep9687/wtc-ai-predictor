# backend/main.py
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from backend.wtc_engine import (
    Fixture,
    compute_standings,
    run_monte_carlo_simulation,
    compute_match_leverage,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = FastAPI(
    title="WTC 2025-2027 AI Predictor API",
    version="1.0.0",
    description="Probabilistic forecasting and scenario simulation engine for the ICC World Test Championship.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def clean_nan_values(obj: Any) -> Any:
    """Recursively replaces float('nan') with None to ensure JSON compliance."""
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan_values(x) for x in obj]
    return obj


def load_fixtures_from_disk() -> Tuple[List[Fixture], List[Dict[str, Any]]]:
    file_path = DATA_DIR / "fixtures_with_predictions.json"
    if not file_path.exists():
        file_path = DATA_DIR / "fixtures_2025_2027.json"

    with open(file_path, "r", encoding="utf-8") as f:
        raw_fixtures = json.load(f)

    sanitized_fixtures = clean_nan_values(raw_fixtures)

    fixture_objects = []
    for item in sanitized_fixtures:
        outcome = item.get("outcome")
        if outcome not in ["HOME_WIN", "AWAY_WIN", "DRAW", "TIE"]:
            outcome = None

        fixture_objects.append(
            Fixture(
                match_id=item["match_id"],
                series_name=item.get("series_name", ""),
                home_team=item["home_team"],
                away_team=item["away_team"],
                venue=item.get("venue", ""),
                start_date=item.get("start_date", ""),
                status=item.get("status", "upcoming"),
                outcome=outcome,
                home_penalty=int(item.get("home_penalty") or 0),
                away_penalty=int(item.get("away_penalty") or 0),
                prob_home_win=float(item.get("prob_home_win") or 0.33),
                prob_draw=float(item.get("prob_draw") or 0.34),
                prob_away_win=float(item.get("prob_away_win") or 0.33),
            )
        )
    return fixture_objects, sanitized_fixtures


class SimulateRequest(BaseModel):
    user_picks: Dict[str, str] = Field(default_factory=dict)
    user_penalties: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    n_simulations: int = Field(default=5000, ge=1000, le=20000)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "cycle": "WTC 2025-2027"}


@app.get("/api/wtc-state")
def get_wtc_state():
    fixtures, raw_list = load_fixtures_from_disk()

    standings = compute_standings(fixtures)
    top2_probs = run_monte_carlo_simulation(fixtures, n_simulations=5000)

    standings_payload = []
    for rank, team in enumerate(standings, 1):
        team.top2_prob = top2_probs.get(team.code, 0.0)
        standings_payload.append(
            {
                "rank": rank,
                "code": team.code,
                "name": team.name,
                "matches": team.matches,
                "wins": team.wins,
                "losses": team.losses,
                "draws": team.draws,
                "ties": team.ties,
                "penalty_points": team.penalty_points,
                "points": team.points,
                "pct": team.pct,
                "top2_prob": team.top2_prob,
            }
        )

    return {
        "standings": standings_payload,
        "fixtures": raw_list,
    }


@app.post("/api/simulate")
def simulate_scenarios(req: SimulateRequest):
    fixtures, _ = load_fixtures_from_disk()

    updated_standings = compute_standings(
        fixtures=fixtures,
        user_picks=req.user_picks,
        user_penalties=req.user_penalties,
    )

    sim_top2 = run_monte_carlo_simulation(
        fixtures=fixtures,
        user_picks=req.user_picks,
        user_penalties=req.user_penalties,
        n_simulations=req.n_simulations,
    )

    standings_payload = []
    for rank, team in enumerate(updated_standings, 1):
        team.top2_prob = sim_top2.get(team.code, 0.0)
        standings_payload.append(
            {
                "rank": rank,
                "code": team.code,
                "name": team.name,
                "matches": team.matches,
                "wins": team.wins,
                "losses": team.losses,
                "draws": team.draws,
                "ties": team.ties,
                "penalty_points": team.penalty_points,
                "points": team.points,
                "pct": team.pct,
                "top2_prob": team.top2_prob,
            }
        )

    return {
        "standings": standings_payload,
        "user_picks_applied": len(req.user_picks),
    }


@app.get("/api/leverage/{match_id}")
def get_match_leverage(match_id: str):
    fixtures, _ = load_fixtures_from_disk()
    match_exists = any(f.match_id == match_id for f in fixtures)
    if not match_exists:
        raise HTTPException(status_code=404, detail=f"Match ID '{match_id}' not found.")

    leverage_data = compute_match_leverage(fixtures, target_match_id=match_id)
    return {"match_id": match_id, "leverage": leverage_data}