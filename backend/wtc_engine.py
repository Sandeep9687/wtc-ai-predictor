# backend/wtc_engine.py
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import numpy as np

# Official ICC WTC 2025-2027 Points System
POINTS_WIN = 12
POINTS_TIE = 6
POINTS_DRAW = 4
POINTS_LOSS = 0
MAX_POINTS_PER_MATCH = 12


@dataclass
class TeamStanding:
    code: str
    name: str
    matches: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    ties: int = 0
    penalty_points: int = 0
    points: int = 0
    pct: float = 0.0
    top2_prob: float = 0.0  # Populated by Monte Carlo engine

    def recalculate_pct(self):
        raw_points = (
            (self.wins * POINTS_WIN)
            + (self.ties * POINTS_TIE)
            + (self.draws * POINTS_DRAW)
            - self.penalty_points
        )
        self.points = max(0, raw_points)
        max_possible = self.matches * MAX_POINTS_PER_MATCH
        self.pct = round((self.points / max_possible) * 100.0, 2) if max_possible > 0 else 0.0


@dataclass
class Fixture:
    match_id: str
    series_name: str
    home_team: str
    away_team: str
    venue: str
    start_date: str
    status: str  # "completed" or "upcoming"
    # Official result or user's locked prediction: "HOME_WIN", "AWAY_WIN", "DRAW", "TIE", or None
    outcome: Optional[str] = None
    home_penalty: int = 0
    away_penalty: int = 0
    # AI/ML predicted probabilities for upcoming matches (must sum to 1.0)
    prob_home_win: float = 0.33
    prob_draw: float = 0.34
    prob_away_win: float = 0.33


WTC_TEAMS: Dict[str, str] = {
    "AUS": "Australia",
    "BAN": "Bangladesh",
    "ENG": "England",
    "IND": "India",
    "NZ": "New Zealand",
    "PAK": "Pakistan",
    "SA": "South Africa",
    "SL": "Sri Lanka",
    "WI": "West Indies",
}


def compute_standings(
    fixtures: List[Fixture],
    user_picks: Optional[Dict[str, str]] = None,
    user_penalties: Optional[Dict[str, Dict[str, int]]] = None,
) -> List[TeamStanding]:
    """
    Calculates the deterministic WTC Points Table combining completed matches
    and any user-selected outcomes/penalties for upcoming matches.
    """
    user_picks = user_picks or {}
    user_penalties = user_penalties or {}

    table: Dict[str, TeamStanding] = {
        code: TeamStanding(code=code, name=name) for code, name in WTC_TEAMS.items()
    }

    for f in fixtures:
        effective_outcome = user_picks.get(f.match_id, f.outcome)
        if not effective_outcome:
            continue

        pen_override = user_penalties.get(f.match_id, {})
        h_pen = pen_override.get("home", f.home_penalty)
        a_pen = pen_override.get("away", f.away_penalty)

        home = table[f.home_team]
        away = table[f.away_team]

        home.matches += 1
        away.matches += 1
        home.penalty_points += h_pen
        away.penalty_points += a_pen

        if effective_outcome == "HOME_WIN":
            home.wins += 1
            away.losses += 1
        elif effective_outcome == "AWAY_WIN":
            away.wins += 1
            home.losses += 1
        elif effective_outcome == "DRAW":
            home.draws += 1
            away.draws += 1
        elif effective_outcome == "TIE":
            home.ties += 1
            away.ties += 1

    for team in table.values():
        team.recalculate_pct()

    # Sort by PCT% descending, then Wins descending, then Points descending
    sorted_teams = sorted(
        table.values(),
        key=lambda t: (t.pct, t.wins, t.points),
        reverse=True,
    )
    return sorted_teams


def run_monte_carlo_simulation(
    fixtures: List[Fixture],
    user_picks: Optional[Dict[str, str]] = None,
    user_penalties: Optional[Dict[str, Dict[str, int]]] = None,
    n_simulations: int = 10000,
    random_seed: int = 42,
) -> Dict[str, float]:
    """
    Runs vectorized Monte Carlo simulations across all unlocked upcoming fixtures
    using AI match probabilities to compute each team's Top-2 qualification %.
    """
    user_picks = user_picks or {}
    user_penalties = user_penalties or {}
    rng = np.random.default_rng(random_seed)

    team_codes = list(WTC_TEAMS.keys())
    team_idx = {code: i for i, code in enumerate(team_codes)}
    num_teams = len(team_codes)

    base_points = np.zeros(num_teams, dtype=np.float64)
    total_matches = np.zeros(num_teams, dtype=np.float64)

    unlocked_fixtures: List[Fixture] = []

    for f in fixtures:
        h_idx = team_idx[f.home_team]
        a_idx = team_idx[f.away_team]

        total_matches[h_idx] += 1
        total_matches[a_idx] += 1

        pen_override = user_penalties.get(f.match_id, {})
        h_pen = pen_override.get("home", f.home_penalty)
        a_pen = pen_override.get("away", f.away_penalty)

        base_points[h_idx] -= h_pen
        base_points[a_idx] -= a_pen

        locked_outcome = user_picks.get(f.match_id, f.outcome)
        if locked_outcome:
            if locked_outcome == "HOME_WIN":
                base_points[h_idx] += POINTS_WIN
            elif locked_outcome == "AWAY_WIN":
                base_points[a_idx] += POINTS_WIN
            elif locked_outcome == "DRAW":
                base_points[h_idx] += POINTS_DRAW
                base_points[a_idx] += POINTS_DRAW
            elif locked_outcome == "TIE":
                base_points[h_idx] += POINTS_TIE
                base_points[a_idx] += POINTS_TIE
        else:
            unlocked_fixtures.append(f)

    # Shape: (n_simulations, num_teams)
    sim_points = np.tile(base_points, (n_simulations, 1))

    # Vectorized sampling for all unpicked upcoming matches
    for f in unlocked_fixtures:
        h_idx = team_idx[f.home_team]
        a_idx = team_idx[f.away_team]

        probs = np.array([f.prob_home_win, f.prob_draw, f.prob_away_win], dtype=np.float64)
        probs = probs / probs.sum()  # Normalize safety check

        # 0 = Home Win, 1 = Draw, 2 = Away Win
        outcomes = rng.choice(3, size=n_simulations, p=probs)

        home_Mask = outcomes == 0
        draw_Mask = outcomes == 1
        away_Mask = outcomes == 2

        sim_points[home_Mask, h_idx] += POINTS_WIN
        sim_points[draw_Mask, h_idx] += POINTS_DRAW
        sim_points[draw_Mask, a_idx] += POINTS_DRAW
        sim_points[away_Mask, a_idx] += POINTS_WIN

    max_points = np.maximum(total_matches * MAX_POINTS_PER_MATCH, 1.0)
    sim_pct = (sim_points / max_points) * 100.0

    # Add tiny random jitter to break exact ties fairly in vectorized sorting
    sim_pct_jittered = sim_pct + rng.uniform(0, 1e-6, size=sim_pct.shape)

    # Identify Top 2 teams in each of the 10,000 simulations
    top2_indices = np.argsort(sim_pct_jittered, axis=1)[:, -2:]
    top2_counts = np.zeros(num_teams, dtype=np.int64)
    for col in range(2):
        counts = np.bincount(top2_indices[:, col], minlength=num_teams)
        top2_counts += counts

    return {
        team_codes[i]: round((top2_counts[i] / n_simulations) * 100.0, 1)
        for i in range(num_teams)
    }


def compute_match_leverage(
    fixtures: List[Fixture],
    target_match_id: str,
    user_picks: Optional[Dict[str, str]] = None,
) -> Dict[str, Dict[str, float]]:
    """
    Calculates how much a single upcoming Test swings Top-2 qualification odds
    for both the Home and Away team ("Must-Win Index").
    """
    user_picks = dict(user_picks or {})
    target = next((f for f in fixtures if f.match_id == target_match_id), None)
    if not target:
        return {}

    baseline = run_monte_carlo_simulation(fixtures, user_picks, n_simulations=4000)

    picks_home = {**user_picks, target_match_id: "HOME_WIN"}
    if_home = run_monte_carlo_simulation(fixtures, picks_home, n_simulations=4000)

    picks_away = {**user_picks, target_match_id: "AWAY_WIN"}
    if_away = run_monte_carlo_simulation(fixtures, picks_away, n_simulations=4000)

    picks_draw = {**user_picks, target_match_id: "DRAW"}
    if_draw = run_monte_carlo_simulation(fixtures, picks_draw, n_simulations=4000)

    h, a = target.home_team, target.away_team
    return {
        h: {
            "baseline": baseline[h],
            "if_win": if_home[h],
            "if_draw": if_draw[h],
            "if_loss": if_away[h],
            "swing": round(if_home[h] - if_away[h], 1),
        },
        a: {
            "baseline": baseline[a],
            "if_win": if_away[a],
            "if_draw": if_draw[a],
            "if_loss": if_home[a],
            "swing": round(if_away[a] - if_home[a], 1),
        },
    }


if __name__ == "__main__":
    # Quick sanity test with sample 2025-27 WTC fixtures
    sample_fixtures = [
        Fixture("M1", "ENG vs IND 2025", "ENG", "IND", "Lord's", "2025-06-20", "completed", outcome="HOME_WIN", home_penalty=2),
        Fixture("M2", "ENG vs IND 2025", "ENG", "IND", "Edgbaston", "2025-07-02", "completed", outcome="AWAY_WIN"),
        Fixture("M3", "AUS vs SA 2026", "AUS", "SA", "Gabba", "2026-11-22", "upcoming", prob_home_win=0.58, prob_draw=0.14, prob_away_win=0.28),
        Fixture("M4", "IND vs AUS 2027", "IND", "AUS", "Mumbai", "2027-01-15", "upcoming", prob_home_win=0.52, prob_draw=0.18, prob_away_win=0.30),
    ]

    standings = compute_standings(sample_fixtures)
    top2_odds = run_monte_carlo_simulation(sample_fixtures, n_simulations=10000)
    leverage = compute_match_leverage(sample_fixtures, "M3")

    print("\n=== WTC 2025-27 ENGINE TEST ===")
    print(f"{'Pos':<4} {'Team':<15} {'M':<3} {'W':<3} {'L':<3} {'D':<3} {'Pen':<4} {'Pts':<5} {'PCT%':<7} {'Top-2 Odds'}")
    print("-" * 68)
    for idx, t in enumerate(standings, 1):
        t.top2_prob = top2_odds[t.code]
        print(f"{idx:<4} {t.name:<15} {t.matches:<3} {t.wins:<3} {t.losses:<3} {t.draws:<3} {t.penalty_points:<4} {t.points:<5} {t.pct:<7.2f} {t.top2_prob:.1f}%")

    print("\n=== MATCH M3 (AUS vs SA at Gabba) QUALIFICATION LEVERAGE ===")
    for team_code, stats in leverage.items():
        print(f"{team_code}: Baseline {stats['baseline']}% -> If Win: {stats['if_win']}% | If Loss: {stats['if_loss']}% (Total Swing: {stats['swing']}%)")