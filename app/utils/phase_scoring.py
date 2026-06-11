"""Shared tactical phase scoring model for A/B/C/D comparisons."""

from __future__ import annotations

import pandas as pd


def _clip01_to_100(v: float) -> float:
    return max(0.0, min(100.0, float(v)))


def _safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b else 0.0


def _ppda(events: pd.DataFrame, team_id: str, opp_id: str) -> float:
    opp_passes_att = events[
        (events["contestant_id"] == opp_id)
        & (events["is_pass"])
        & (events["x"] >= 40)
    ]
    team_def_actions = events[
        (events["contestant_id"] == team_id)
        & (events["type_id"].isin({7, 8, 49}))
        & (events["x"] >= 40)
    ]
    return _safe_div(len(opp_passes_att), len(team_def_actions) or 1)


def phase_scores_from_events(events: pd.DataFrame, team_id: str, opp_id: str) -> dict[str, float]:
    if events.empty:
        return {
            "A. Offensive Moment": 0.0,
            "B. Defensive Transition": 0.0,
            "C. Defensive Moment": 0.0,
            "D. Offensive Transition": 0.0,
        }

    team = events[events["contestant_id"] == team_id]
    opp = events[events["contestant_id"] == opp_id]
    team_pass = team[team["is_pass"]]
    ppda = _ppda(events, team_id, opp_id)

    pass_acc = float(team_pass["outcome"].mean() * 100) if not team_pass.empty else 0.0
    xg_sum = float(team["xg"].fillna(0).sum())
    shots = int(team["is_shot"].sum())
    opp_shots = int(opp["is_shot"].sum())
    recoveries = int(team["is_recovery"].sum())
    inter = int(team["is_interception"].sum())
    tackles = int(team["is_tackle"].sum())

    # D transition: regains leading to shot within 15s
    reg = team[team["is_recovery"] | team["is_interception"] | team["is_tackle"]].copy()
    trans_rate = 0.0
    if not reg.empty:
        ordered = events.sort_values(["period", "minute", "second", "event_id"]).copy()
        ordered["t"] = ordered["minute"].fillna(0).astype(int) * 60 + ordered["second"].fillna(0).astype(int)
        reg["t"] = reg["minute"].fillna(0).astype(int) * 60 + reg["second"].fillna(0).astype(int)
        trans = 0
        for _, r in reg.iterrows():
            win = ordered[
                (ordered["contestant_id"] == team_id)
                & (ordered["t"] >= r["t"])
                & (ordered["t"] <= r["t"] + 15)
            ]
            if not win[win["is_shot"]].empty:
                trans += 1
        trans_rate = _safe_div(trans, len(reg)) * 100

    a = (pass_acc * 0.45) + (xg_sum * 10 * 0.35) + (shots * 2.5 * 0.20)
    b = ((100.0 / (1.0 + ppda)) * 0.55) + ((recoveries + inter) * 1.8 * 0.45)
    c = ((100.0 / (1.0 + ppda)) * 0.40) + (max(0.0, 40.0 - opp_shots * 2.0) * 0.60)
    d = (trans_rate * 0.65) + (xg_sum * 7.0 * 0.35)

    return {
        "A. Offensive Moment": _clip01_to_100(a),
        "B. Defensive Transition": _clip01_to_100(b),
        "C. Defensive Moment": _clip01_to_100(c),
        "D. Offensive Transition": _clip01_to_100(d),
    }


def phase_scores_from_team_row(row: pd.Series) -> dict[str, float]:
    pass_acc = float(row.get("pass_acc", 0))
    ppda = float(row.get("ppda", 0))
    goals_pg = float(row.get("goals_per_game", 0))
    conceded_pg = float(row.get("conceded_per_game", 0))
    xg_pg = float(row.get("xg_per_game", 0))
    shots_pg = float(row.get("shots_per_game", 0))
    def_actions_pg = float(row.get("def_actions_pg", 0))

    a = (pass_acc * 0.45) + (xg_pg * 20 * 0.35) + (goals_pg * 20 * 0.20)
    b = ((100.0 / (1.0 + ppda)) * 0.55) + (def_actions_pg * 2.0 * 0.45)
    c = ((100.0 / (1.0 + ppda)) * 0.40) + ((5 - min(5, conceded_pg)) * 20 * 0.60)
    d = (shots_pg * 6 * 0.50) + (xg_pg * 20 * 0.50)

    return {
        "A. Offensive Moment": _clip01_to_100(a),
        "B. Defensive Transition": _clip01_to_100(b),
        "C. Defensive Moment": _clip01_to_100(c),
        "D. Offensive Transition": _clip01_to_100(d),
    }
