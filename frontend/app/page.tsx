"use client";

import React, { useEffect, useState } from "react";
import {
  Sparkles,
  RotateCcw,
  Play,
  Trophy,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  BrainCircuit,
  MapPin,
  Calendar,
} from "lucide-react";

interface Standing {
  rank: number;
  code: string;
  name: string;
  matches: number;
  wins: number;
  losses: number;
  draws: number;
  penalty_points: number;
  points: number;
  pct: number;
  top2_prob: number;
}

interface Fixture {
  match_id: string;
  series_name: string;
  home_team: string;
  away_team: string;
  venue: string;
  start_date: string;
  status: "completed" | "upcoming";
  outcome: string | null;
  home_penalty: number;
  away_penalty: number;
  prob_home_win: number;
  prob_draw: number;
  prob_away_win: number;
  insights?: string[];
}

export default function WtcPredictorPage() {
  const [standings, setStandings] = useState<Standing[]>([]);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [userPicks, setUserPicks] = useState<Record<string, string>>({});
  const [expandedInsights, setExpandedInsights] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [simulating, setSimulating] = useState<boolean>(false);

  const loadInitialState = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/wtc-state");
      const data = await res.json();
      setStandings(data.standings || []);
      setFixtures(data.fixtures || []);
    } catch (err) {
      console.error("Failed to load WTC data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialState();
  }, []);

  const runSimulation = async (updatedPicks: Record<string, string>) => {
    try {
      setSimulating(true);
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_picks: updatedPicks, n_simulations: 5000 }),
      });
      const data = await res.json();
      setStandings(data.standings || []);
    } catch (err) {
      console.error("Simulation failed:", err);
    } finally {
      setSimulating(false);
    }
  };

  const handlePick = (matchId: string, outcome: string) => {
    const newPicks = { ...userPicks, [matchId]: outcome };
    setUserPicks(newPicks);
    runSimulation(newPicks);
  };

  const handleAutoFillWithAi = () => {
    const aiPicks: Record<string, string> = { ...userPicks };
    fixtures.forEach((f) => {
      if (f.status === "upcoming" && !aiPicks[f.match_id]) {
        if (f.prob_home_win >= f.prob_away_win && f.prob_home_win >= f.prob_draw) {
          aiPicks[f.match_id] = "HOME_WIN";
        } else if (f.prob_away_win >= f.prob_home_win && f.prob_away_win >= f.prob_draw) {
          aiPicks[f.match_id] = "AWAY_WIN";
        } else {
          aiPicks[f.match_id] = "DRAW";
        }
      }
    });
    setUserPicks(aiPicks);
    runSimulation(aiPicks);
  };

  const handleResetPicks = () => {
    setUserPicks({});
    loadInitialState();
  };

  const toggleInsight = (matchId: string) => {
    setExpandedInsights((prev) => ({ ...prev, [matchId]: !prev[matchId] }));
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-10">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-cricket-border">
        <div>
          <div className="flex items-center gap-3">
            <Trophy className="w-8 h-8 text-yellow-400" />
            <h1 className="text-3xl font-extrabold tracking-tight">WTC 2025–2027 Predictor</h1>
            <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2.5 py-1 rounded-full font-semibold border border-emerald-500/30">
              AI Powered
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Simulate paths to the Lord&apos;s Final using probabilistic LightGBM match projections.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={handleAutoFillWithAi}
            disabled={simulating || loading}
            className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 px-4 py-2.5 rounded-lg text-sm font-semibold shadow-md transition disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4 text-blue-200" />
            Auto-Fill AI Favorites
          </button>
          <button
            onClick={() => runSimulation(userPicks)}
            disabled={simulating || loading}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 px-4 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            <Play className={`w-4 h-4 text-emerald-400 ${simulating ? "animate-spin" : ""}`} />
            {simulating ? "Simulating..." : "Re-Simulate (5k)"}
          </button>
          <button
            onClick={handleResetPicks}
            disabled={simulating || loading || Object.keys(userPicks).length === 0}
            className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 px-3.5 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 transition disabled:opacity-40"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
        </div>
      </header>

      <section className="bg-cricket-card border border-cricket-border rounded-xl shadow-2xl overflow-hidden sticky top-4 z-50">
        <div className="p-4 bg-slate-900/90 backdrop-blur-sm border-b border-cricket-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            <h2 className="font-bold text-lg text-slate-200">Current &amp; Projected Standings</h2>
          </div>
          <span className="text-xs text-slate-400">Top 2 qualify for the Final</span>
        </div>

        <div className="overflow-x-auto max-h-[40vh] overflow-y-auto">
          <table className="w-full text-left text-sm relative">
            <thead className="bg-slate-950/90 backdrop-blur-sm text-slate-400 font-semibold text-xs uppercase tracking-wider sticky top-0 z-10 shadow-sm border-b border-cricket-border">
              <tr>
                <th className="py-3 px-4">Pos</th>
                <th className="py-3 px-4">Team</th>
                <th className="py-3 px-3 text-center">P</th>
                <th className="py-3 px-3 text-center">W</th>
                <th className="py-3 px-3 text-center">L</th>
                <th className="py-3 px-3 text-center">D</th>
                <th className="py-3 px-3 text-center">Pen</th>
                <th className="py-3 px-3 text-center">Pts</th>
                <th className="py-3 px-4 text-center font-bold text-white">PCT%</th>
                <th className="py-3 px-6 text-left">Final Probability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cricket-border">
              {standings.map((team, idx) => {
                const isTop2 = idx < 2;
                return (
                  <tr
                    key={team.code}
                    className={`transition-colors hover:bg-slate-800/40 ${
                      isTop2 ? "bg-emerald-950/20" : ""
                    }`}
                  >
                    <td className="py-3 px-4 font-bold text-slate-300">
                      <div className="flex items-center gap-2">
                        {isTop2 && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />}
                        {team.rank}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-semibold text-white">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                          {team.code}
                        </span>
                        <span className="hidden md:inline">{team.name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-center text-slate-300">{team.matches}</td>
                    <td className="py-3 px-3 text-center text-emerald-400 font-medium">{team.wins}</td>
                    <td className="py-3 px-3 text-center text-red-400 font-medium">{team.losses}</td>
                    <td className="py-3 px-3 text-center text-slate-400 font-medium">{team.draws}</td>
                    <td className="py-3 px-3 text-center text-yellow-400 font-medium">
                      {team.penalty_points > 0 ? `-${team.penalty_points}` : "0"}
                    </td>
                    <td className="py-3 px-3 text-center font-bold text-slate-100">{team.points}</td>
                    <td className="py-3 px-4 text-center font-extrabold text-base text-emerald-400">
                      {team.pct.toFixed(2)}%
                    </td>
                    <td className="py-3 px-6">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 bg-slate-800 rounded-full h-2.5 overflow-hidden border border-slate-700">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              team.top2_prob >= 50
                                ? "bg-emerald-500"
                                : team.top2_prob >= 20
                                ? "bg-blue-500"
                                : "bg-slate-600"
                            }`}
                            style={{ width: `${Math.min(100, team.top2_prob)}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs font-bold w-10 text-right">
                          {team.top2_prob.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-cricket-border pb-2">
          <h2 className="text-2xl font-bold text-white">Fixtures &amp; Match Predictions</h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {fixtures.map((f) => {
            const isCompleted = f.status === "completed";
            const currentPick = userPicks[f.match_id];
            const pHome = Math.round(f.prob_home_win * 100);
            const pDraw = Math.round(f.prob_draw * 100);
            const pAway = Math.round(f.prob_away_win * 100);

            return (
              <div key={f.match_id} className="bg-cricket-card border border-cricket-border rounded-xl p-4 flex flex-col shadow-sm">
                
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <span className="text-xs font-semibold text-blue-400 bg-blue-500/10 px-2 py-1 rounded">
                      {f.series_name}
                    </span>
                    <div className="flex items-center gap-3 mt-2 text-sm text-slate-400">
                      <div className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5" /> {f.venue}
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" /> {f.start_date}
                      </div>
                    </div>
                  </div>
                  {isCompleted ? (
                    <span className="text-xs font-bold text-slate-400 bg-slate-800 px-2 py-1 rounded">Completed</span>
                  ) : (
                    <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">
                      Upcoming
                    </span>
                  )}
                </div>

                <div className="flex justify-between items-center bg-slate-900/50 p-3 rounded-lg border border-slate-800 mb-4">
                  <div className="text-center w-1/3">
                    <div className="font-bold text-lg text-white">{f.home_team}</div>
                    {!isCompleted && <div className="text-xs text-slate-400">{pHome}% Win</div>}
                  </div>
                  <div className="text-center w-1/3 border-x border-slate-700/50">
                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Draw</div>
                    {!isCompleted && <div className="text-xs text-slate-400 mt-1">{pDraw}% Risk</div>}
                  </div>
                  <div className="text-center w-1/3">
                    <div className="font-bold text-lg text-white">{f.away_team}</div>
                    {!isCompleted && <div className="text-xs text-slate-400">{pAway}% Win</div>}
                  </div>
                </div>

                <div className="mt-auto">
                  {isCompleted ? (
                    <div className="w-full text-center py-2.5 bg-slate-800 rounded-lg text-sm font-semibold text-slate-300 border border-slate-700">
                      Official Result: {f.outcome?.replace("_", " ")}
                    </div>
                  ) : (
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        onClick={() => handlePick(f.match_id, "HOME_WIN")}
                        className={`py-2 rounded-lg text-sm font-semibold transition border ${
                          currentPick === "HOME_WIN"
                            ? "bg-blue-600 border-blue-500 text-white"
                            : "bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700"
                        }`}
                      >
                        {f.home_team} Win
                      </button>
                      <button
                        onClick={() => handlePick(f.match_id, "DRAW")}
                        className={`py-2 rounded-lg text-sm font-semibold transition border ${
                          currentPick === "DRAW"
                            ? "bg-slate-600 border-slate-500 text-white"
                            : "bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700"
                        }`}
                      >
                        Draw
                      </button>
                      <button
                        onClick={() => handlePick(f.match_id, "AWAY_WIN")}
                        className={`py-2 rounded-lg text-sm font-semibold transition border ${
                          currentPick === "AWAY_WIN"
                            ? "bg-indigo-600 border-indigo-500 text-white"
                            : "bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700"
                        }`}
                      >
                        {f.away_team} Win
                      </button>
                    </div>
                  )}
                </div>

                {f.insights && f.insights.length > 0 && (
                  <div className="mt-4 border-t border-slate-800 pt-3">
                    <button
                      onClick={() => toggleInsight(f.match_id)}
                      className="w-full flex items-center justify-between text-xs text-blue-400 hover:text-blue-300 font-semibold"
                    >
                      <span className="flex items-center gap-1.5">
                        <BrainCircuit className="w-4 h-4" /> AI Match Insights
                      </span>
                      {expandedInsights[f.match_id] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                    
                    {expandedInsights[f.match_id] && (
                      <ul className="mt-3 space-y-2">
                        {f.insights.map((insight, i) => (
                          <li key={i} className="text-xs text-slate-300 bg-slate-900 p-2 rounded flex items-start gap-2">
                            <span className="text-blue-500 mt-0.5">•</span> {insight}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}