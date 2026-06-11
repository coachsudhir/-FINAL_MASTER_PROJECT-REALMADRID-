"""Additive KPI extension and cross-phase metric layer."""

from __future__ import annotations

import math
import pandas as pd


def _safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b else 0.0


def _phase_df(events: pd.DataFrame, phase: str, team_id: str) -> pd.DataFrame:
    return events[(events["tactical_phase"] == phase) & (events["contestant_id"] == team_id)]


def build_kpi_extension_tables(events_with_tags: pd.DataFrame, sequence_layer: pd.DataFrame, team_id: str, opp_id: str) -> dict[str, pd.DataFrame]:
    if events_with_tags.empty:
        return {}

    tables: dict[str, pd.DataFrame] = {}

    om = _phase_df(events_with_tags, "Offensive Moment", team_id)
    dt = _phase_df(events_with_tags, "Defensive Transition", opp_id)
    dm = _phase_df(events_with_tags, "Defensive Moment", opp_id)
    ot = _phase_df(events_with_tags, "Offensive Transition", team_id)

    tables["offensive_moment_kpi_extension"] = pd.DataFrame(
        [
            {"kpi": "build_up_exit_rate", "value": _safe_div((om["x"] >= 40).sum(), max(len(om), 1))},
            {"kpi": "final_third_entry_efficiency", "value": _safe_div((om["x"] >= 67).sum(), max(len(om), 1))},
            {"kpi": "box_access_conversion", "value": _safe_div((om["x"] >= 83).sum(), max((om["x"] >= 67).sum(), 1))},
            {"kpi": "phase_xt_yield_proxy", "value": float(om["xg"].fillna(0).sum())},
        ]
    )

    tables["defensive_transition_kpi_extension"] = pd.DataFrame(
        [
            {"kpi": "five_second_regain_proxy", "value": _safe_div((dt["type_id"].isin({7, 8, 49})).sum(), max(len(dt), 1))},
            {"kpi": "counterpress_engagement_rate", "value": _safe_div((dt["sub_phase_tag"] == "DT-2 Counterpress engagement").sum(), max(len(dt), 1))},
            {"kpi": "central_lane_exposure_after_loss", "value": _safe_div(((dt["y"] >= 35) & (dt["y"] <= 65)).sum(), max(len(dt), 1))},
        ]
    )

    tables["defensive_moment_kpi_extension"] = pd.DataFrame(
        [
            {"kpi": "press_trap_success_proxy", "value": _safe_div((dm["type_id"].isin({7, 8})).sum(), max(len(dm), 1))},
            {"kpi": "box_protection_efficiency", "value": _safe_div((dm["type_id"].isin({8, 15, 10})).sum(), max((dm["x"] <= 20).sum(), 1))},
            {"kpi": "shot_quality_suppression_proxy", "value": float(dm["xg"].fillna(0).mean() if not dm.empty else 0)},
        ]
    )

    tables["offensive_transition_kpi_extension"] = pd.DataFrame(
        [
            {"kpi": "launch_speed_proxy", "value": float(ot["event_time_s"].diff().fillna(0).clip(lower=0).median() if not ot.empty else 0)},
            {"kpi": "vertical_gain_per_transition", "value": float(ot["x"].diff().fillna(0).clip(lower=0).mean() if not ot.empty else 0)},
            {"kpi": "transition_finalization_rate", "value": _safe_div((ot["is_shot"]).sum(), max(len(ot), 1))},
            {"kpi": "transition_xt_burst_proxy", "value": float(ot["xg"].fillna(0).sum())},
        ]
    )

    return tables


def build_cross_phase_metrics(events_with_tags: pd.DataFrame, team_id: str) -> pd.DataFrame:
    if events_with_tags.empty:
        return pd.DataFrame()

    team = events_with_tags[events_with_tags["contestant_id"] == team_id]
    if team.empty:
        return pd.DataFrame()

    om = team[team["tactical_phase"] == "Offensive Moment"]
    ot = team[team["tactical_phase"] == "Offensive Transition"]
    dm = events_with_tags[(events_with_tags["contestant_id"] != team_id) & (events_with_tags["tactical_phase"] == "Defensive Moment")]

    transition_dependency_ratio = _safe_div(ot["xg"].fillna(0).sum(), (ot["xg"].fillna(0).sum() + om["xg"].fillna(0).sum()))
    structural_stability_index = 1.0 / (1.0 + float(team.groupby("tactical_phase")["x"].std().fillna(0).mean()))
    phase_dominance_ratio = _safe_div(len(om) + len(ot), len(dm) if len(dm) else 1)
    momentum_contribution_by_phase = float(ot["xg"].fillna(0).sum() - dm["xg"].fillna(0).sum())
    phase_conversion_continuity = _safe_div((team["is_shot"]).sum(), max(team["sequence_id"].nunique(), 1))
    pressure_to_value_efficiency = _safe_div(team[team["type_id"].isin({7, 8, 49})]["xg"].fillna(0).sum(), max((team["type_id"].isin({7, 8, 49})).sum(), 1))

    return pd.DataFrame(
        [
            {"kpi": "transition_dependency_ratio", "value": transition_dependency_ratio},
            {"kpi": "structural_stability_index", "value": structural_stability_index},
            {"kpi": "phase_dominance_ratio", "value": phase_dominance_ratio},
            {"kpi": "momentum_contribution_by_phase", "value": momentum_contribution_by_phase},
            {"kpi": "phase_conversion_continuity", "value": phase_conversion_continuity},
            {"kpi": "pressure_to_value_efficiency", "value": pressure_to_value_efficiency},
        ]
    )
