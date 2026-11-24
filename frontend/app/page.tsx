"use client";

import React, { useEffect, useState } from "react";
import { Sparkles, BrainCircuit, ChevronDown, ChevronUp } from "lucide-react";

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
  prob_home_win: number;
  prob_draw: number;
  prob_away_win: number;
  insights?: string[];
}

const TEAM_COLORS: Record<string, string> = {
  IND: "bg-[#0078FF] text-white",
  AUS: "bg-[#FFCD00] text-black",
  ENG: "bg-[#CE1124] text-white",
  NZ: "bg-[#000000] text-white",
  SA: "bg-[#007A4D] text-white",
  PAK: "bg-[#006629] text-white",
  SL: "bg-[#0033A0] text-white",
  WI: "bg-[#7B0028] text-white",
  BAN: "bg-[#006A4E] text-white",
};

export default function WtcPredictorPage() {
  const [standings, setStandings] = useState<Standing[]>([]);
  const [baselineRanks, setBaselineRanks] = useState<Record<string, number>>({});
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [userPicks, setUserPicks] = useState<Record<string, string>>({});
  const [expandedInsights, setExpandedInsights] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const loadInitialState = async () => {
      const res = await fetch("/api/wtc-state");
      const data = await res.json();
      setStandings(data.standings || []);
      setFixtures(data.fixtures || []);
      
      const ranks: Record<string, number> = {};
      data.standings.forEach((team: Standing) => { ranks[team.code] = team.rank; });
      setBaselineRanks(ranks);
    };
    loadInitialState();
  }, []);

  const runSimulation = async (updatedPicks: Record<string, string>) => {
    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_picks: updatedPicks, n_simulations: 2000 }),
    });
    const data = await res.json();
    setStandings(data.standings || []);
  };

  const handlePick = (matchId: string, outcome: string) => {
    const newPicks = { ...userPicks, [matchId]: outcome };
    setUserPicks(newPicks);
    runSimulation(newPicks);
  };

  const renderRankMovement = (team: Standing) => {
    const baseline = baselineRanks[team.code];
    if (!baseline || baseline === team.rank) return <span className="text-slate-300 text-[10px]">●</span>;
    const diff = baseline - team.rank;
    if (diff > 0) return <span className="text-green-500 font-bold text-xs flex items-center"><ChevronUp className="w-3 h-3 -mr-0.5"/>{diff}</span>;
    return <span className="text-red-500 font-bold text-xs flex items-center"><ChevronDown className="w-3 h-3 -mr-0.5"/>{Math.abs(diff)}</span>;
  };

  const getTeamColorClass = (team: string, role: "HOME" | "AWAY", f: Fixture, currentPick: string) => {
    const isCompleted = f.status === "completed";
    const isActive = (isCompleted && f.outcome === `${role}_WIN`) || (!isCompleted && currentPick === `${role}_WIN`);
    return isActive ? TEAM_COLORS[team] || "bg-slate-800 text-white" : "bg-[#C4C4C4] text-white hover:bg-slate-400";
  };

  const getMiddleText = (f: Fixture) => {
    if (f.status === "upcoming") return "Draw";
    if (f.outcome === "HOME_WIN") return "Def";
    if (f.outcome === "AWAY_WIN") return "Def By";
    return "Draw";
  };

  return (
    <div className="max-w-[1300px] mx-auto px-4 py-8 bg-slate-50 min-h-screen">
      
      <header className="flex justify-between items-end mb-8 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-3xl font-extrabold text-[#1a237e] tracking-tight">WTC 2025–2027 Predictor</h1>
        </div>
      </header>

      <div className="flex flex-col lg:flex-row gap-8 items-start">
        
        {/* Left Column: Match List */}
        <div className="w-full lg:w-[60%] flex flex-col gap-6">
          {fixtures.map((f) => {
            const isCompleted = f.status === "completed";
            const currentPick = userPicks[f.match_id];

            return (
              <div key={f.match_id} className="bg-white border-b border-slate-200 py-4 shadow-sm rounded-lg">
                
                <div className="text-center mb-3">
                  <h3 className="font-bold text-lg text-slate-800">{f.home_team} vs {f.away_team}</h3>
                  <p className="text-xs text-slate-500">{f.start_date}</p>
                </div>
                
                <div className="flex h-14 mx-auto max-w-[90%] md:max-w-lg rounded overflow-hidden">
                  <button 
                    onClick={() => !isCompleted && handlePick(f.match_id, "HOME_WIN")}
                    className={`flex-1 flex flex-col justify-center items-center font-extrabold text-xl uppercase transition-colors ${getTeamColorClass(f.home_team, "HOME", f, currentPick)}`}
                  >
                    {f.home_team}
                  </button>

                  <button 
                    onClick={() => !isCompleted && handlePick(f.match_id, "DRAW")}
                    className={`w-20 flex items-center justify-center font-semibold text-sm transition-colors ${
                      (isCompleted && f.outcome === "DRAW") || (!isCompleted && currentPick === "DRAW")
                      ? "bg-slate-500 text-white" : "bg-[#f4f4f4] text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {getMiddleText(f)}
                  </button>

                  <button 
                    onClick={() => !isCompleted && handlePick(f.match_id, "AWAY_WIN")}
                    className={`flex-1 flex flex-col justify-center items-center font-extrabold text-xl uppercase transition-colors ${getTeamColorClass(f.away_team, "AWAY", f, currentPick)}`}
                  >
                    {f.away_team}
                  </button>
                </div>

                <div className="flex justify-between items-center mt-3 max-w-[90%] md:max-w-lg mx-auto px-1">
                  <span className="text-xs text-slate-500 hover:text-slate-800 cursor-pointer">More Options +</span>
                  {f.insights && f.insights.length > 0 && (
                    <button onClick={() => setExpandedInsights(prev => ({...prev, [f.match_id]: !prev[f.match_id]}))} className="flex items-center gap-1 text-xs text-emerald-600 font-bold bg-emerald-50 px-2 py-1 rounded">
                      <BrainCircuit className="w-3.5 h-3.5" /> AI Insights
                    </button>
                  )}
                </div>

                {expandedInsights[f.match_id] && (
                  <div className="max-w-[90%] md:max-w-lg mx-auto mt-2 bg-slate-50 border border-slate-200 p-3 rounded text-xs text-slate-600">
                    <div className="flex justify-between font-mono mb-2 text-slate-400">
                      <span>{f.home_team}: {Math.round(f.prob_home_win*100)}%</span>
                      <span>Draw: {Math.round(f.prob_draw*100)}%</span>
                      <span>{f.away_team}: {Math.round(f.prob_away_win*100)}%</span>
                    </div>
                    {f.insights?.map((ins, i) => <div key={i}>• {ins}</div>)}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Right Column: Sticky Table */}
        <div className="w-full lg:w-[40%] sticky top-4">
          <div className="bg-white border border-slate-200 shadow-sm rounded-lg overflow-hidden">
            <div className="p-4 border-b border-slate-200">
              <h2 className="font-extrabold text-[22px] text-[#1a237e] uppercase tracking-tight">WTC Standings Table</h2>
              <p className="text-[11px] text-slate-500 mt-1">
                The table will change automatically based on your predictions. The actual table is updated at the conclusion of a Test Series.
              </p>
            </div>
            
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-white">
                <tr className="border-b-2 border-emerald-500">
                  <th className="py-3 px-3 text-slate-500 font-bold text-[10px] uppercase text-center w-8">Pos</th>
                  <th className="py-3 px-1 w-4"></th>
                  <th className="py-3 px-2 text-slate-500 font-bold text-[10px] uppercase">Team</th>
                  <th className="py-3 px-3 text-slate-800 font-bold text-[10px] uppercase text-center">PCT</th>
                  <th className="py-3 px-2 text-slate-500 font-bold text-[10px] uppercase text-center">Played</th>
                  <th className="py-3 px-2 text-slate-500 font-bold text-[10px] uppercase text-center">Won</th>
                  <th className="py-3 px-2 text-slate-500 font-bold text-[10px] uppercase text-center">Draw</th>
                  <th className="py-3 px-2 text-slate-500 font-bold text-[10px] uppercase text-center">Lost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {standings.map((team) => (
                  <tr key={team.code} className="hover:bg-slate-50">
                    <td className="py-3.5 px-3 font-bold text-slate-800 text-center">{team.rank}</td>
                    <td className="py-3.5 px-0 text-center">{renderRankMovement(team)}</td>
                    <td className="py-3.5 px-2 font-bold text-[#1a237e] uppercase">{team.name}</td>
                    <td className="py-3.5 px-3 text-center font-extrabold text-[#1a237e] text-[15px]">{team.pct.toFixed(2)}</td>
                    <td className="py-3.5 px-2 text-center font-bold text-[#1a237e]">{team.matches}</td>
                    <td className="py-3.5 px-2 text-center font-bold text-[#1a237e]">{team.wins}</td>
                    <td className="py-3.5 px-2 text-center font-bold text-[#1a237e]">{team.draws}</td>
                    <td className="py-3.5 px-2 text-center font-bold text-[#1a237e]">{team.losses}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}