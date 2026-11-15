# backend/update_results.py
import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# 1. Securely load API Key from .env file
load_dotenv()
API_KEY = os.getenv("CRICKET_API_KEY")

DATA_DIR = Path(__file__).resolve().parent / "data"
FIXTURES_FILE = DATA_DIR / "fixtures_2025_2027.json"

# Map full API team names to our 3-letter codes
TEAM_MAP = {
    "India": "IND", "Australia": "AUS", "England": "ENG",
    "New Zealand": "NZ", "South Africa": "SA", "Pakistan": "PAK",
    "Sri Lanka": "SL", "West Indies": "WI", "Bangladesh": "BAN"
}

def fetch_and_update_matches():
    if not API_KEY:
        print("❌ Error: CRICKET_API_KEY not found in .env file.")
        return

    print("Fetching latest match results from CricketData API...")
    url = f"https://api.cricketdata.org/v1/matches?apikey={API_KEY}&offset=0"
    
    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print(f"❌ API Request Failed: {e}")
        return

    if data.get("status") != "success":
        print("❌ Failed to authenticate with API. Check your API Key.")
        return

    # Load our existing WTC fixtures
    with open(FIXTURES_FILE, "r") as f:
        fixtures = json.load(f)

    updated_count = 0

    for match in data.get("data", []):
        # We only care about completed Test Matches
        if match.get("matchType") != "test" or match.get("status") != "Match ended":
            continue

        team1 = match["teamInfo"][0]["name"]
        team2 = match["teamInfo"][1]["name"]
        
        code1 = TEAM_MAP.get(team1)
        code2 = TEAM_MAP.get(team2)

        # Skip if teams are not part of the WTC cycle (e.g., Zimbabwe, Ireland)
        if not code1 or not code2:
            continue

        match_status_text = match.get("statusText", "").lower()
        
        # Determine the winner from the API text (e.g., "India won by 434 runs")
        outcome = "DRAW"
        winner_code = None
        
        if team1.lower() in match_status_text and "won" in match_status_text:
            winner_code = code1
        elif team2.lower() in match_status_text and "won" in match_status_text:
            winner_code = code2
        elif "draw" not in match_status_text:
            continue # In case of abandoned matches

        # Find the next upcoming match between these two teams in our JSON
        for f in fixtures:
            if f["status"] == "upcoming" and (f["home_team"] in [code1, code2]) and (f["away_team"] in [code1, code2]):
                
                if outcome != "DRAW":
                    outcome = "HOME_WIN" if f["home_team"] == winner_code else "AWAY_WIN"
                
                f["status"] = "completed"
                f["outcome"] = outcome
                
                print(f"✅ Match Updated: {f['home_team']} vs {f['away_team']} -> {outcome}")
                updated_count += 1
                break # Only update the first chronological upcoming match between them

    # Save the updated fixtures and rebuild the ML predictions
    if updated_count > 0:
        with open(FIXTURES_FILE, "w") as f:
            json.dump(fixtures, f, indent=2)
            
        print(f"🎉 Successfully saved {updated_count} new match result(s).")
        print("Re-running Machine Learning pipeline...")
        
        # Re-run data pipeline to update probabilities for remaining matches
        os.system("python backend/data_pipeline.py")
        os.system("python backend/ml_predictor.py")
        print("✅ Pipeline complete! The Next.js frontend table will now reflect the live updates.")
    else:
        print("No new completed WTC matches found to update.")

if __name__ == "__main__":
    fetch_and_update_matches()