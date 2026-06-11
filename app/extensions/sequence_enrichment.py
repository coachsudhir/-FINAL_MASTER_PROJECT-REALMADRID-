"""Sequence enrichment layer (add-only).

Builds possession-level metadata without modifying baseline possession logic.
"""

from __future__ import annotations

import pandas as pd


def enrich_sequences(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (events_with_sequence_metadata, sequence_enrichment_layer).

    Rules are deterministic and derived from event order, team changes, and time gaps.
    """
    if events.empty:
        return events.copy(), pd.DataFrame()

    df = events.copy().sort_values(["period", "minute", "second", "event_id"]).reset_index(drop=True)
    df["event_time_s"] = (df["minute"].fillna(0).astype(int) * 60) + df["second"].fillna(0).astype(int)

    seq_id = 0
    seq_ids: list[int] = []
    prev_team = None
    prev_period = None
    prev_t = None

    for _, row in df.iterrows():
        team = row.get("contestant_id")
        period = row.get("period")
        t = row.get("event_time_s")

        new_seq = False
        if prev_team is None:
            new_seq = True
        elif period != prev_period:
            new_seq = True
        elif team != prev_team:
            new_seq = True
        elif prev_t is not None and t is not None and (t - prev_t) > 15:
            new_seq = True

        if new_seq:
            seq_id += 1

        seq_ids.append(seq_id)
        prev_team = team
        prev_period = period
        prev_t = t

    df["sequence_id"] = seq_ids

    seq = (
        df.groupby("sequence_id", as_index=False)
        .agg(
            team_id=("contestant_id", "first"),
            period=("period", "first"),
            start_time_s=("event_time_s", "min"),
            end_time_s=("event_time_s", "max"),
            n_events=("event_id", "count"),
            start_x=("x", "first"),
            end_x=("x", "last"),
            passes=("is_pass", "sum"),
            shots=("is_shot", "sum"),
            goals=("is_goal", "sum"),
            xg_sum=("xg", "sum"),
        )
        .sort_values("sequence_id")
        .reset_index(drop=True)
    )

    seq["duration_s"] = (seq["end_time_s"] - seq["start_time_s"]).clip(lower=0)
    seq["progression_x"] = (seq["end_x"] - seq["start_x"]).fillna(0)
    seq["is_finalization_seq"] = seq["shots"] > 0

    seq["prev_team_id"] = seq["team_id"].shift(1)
    seq["next_team_id"] = seq["team_id"].shift(-1)
    seq["is_regain"] = seq["team_id"] != seq["prev_team_id"]
    seq["is_loss_next"] = seq["team_id"] != seq["next_team_id"]

    df = df.merge(
        seq[["sequence_id", "start_time_s", "duration_s", "progression_x", "is_finalization_seq"]],
        on="sequence_id",
        how="left",
    )

    return df, seq
