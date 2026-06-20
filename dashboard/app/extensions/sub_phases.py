"""Tactical sub-phase tagging (add-only).

Maps events to additive sub-phase tags for OM, DT, DM, OT.
"""

from __future__ import annotations

import pandas as pd


def tag_sub_phases(events: pd.DataFrame, sequence_layer: pd.DataFrame, team_id: str, opp_id: str) -> pd.DataFrame:
    if events.empty:
        out = events.copy()
        out["tactical_phase"] = []
        out["sub_phase_tag"] = []
        return out

    df = events.copy()
    df["tactical_phase"] = ""
    df["sub_phase_tag"] = ""

    seq_map = sequence_layer.set_index("sequence_id") if not sequence_layer.empty else None

    for idx, row in df.iterrows():
        seq_id = row.get("sequence_id")
        is_rm = row.get("contestant_id") == team_id

        seq = None
        if seq_map is not None and seq_id in seq_map.index:
            seq = seq_map.loc[seq_id]

        if is_rm:
            # Offensive side: OM vs OT
            if seq is not None and seq.get("duration_s", 999) <= 15 and seq.get("is_regain", False):
                df.at[idx, "tactical_phase"] = "Offensive Transition"
                prog = float(seq.get("progression_x", 0) or 0)
                if row.get("is_shot", False):
                    df.at[idx, "sub_phase_tag"] = "OT-4 Finalization window"
                elif prog >= 30:
                    df.at[idx, "sub_phase_tag"] = "OT-2 Vertical break"
                elif row.get("is_pass", False) and row.get("x", 0) < 50:
                    df.at[idx, "sub_phase_tag"] = "OT-1 Regain-to-launch"
                elif seq.get("is_finalization_seq", False):
                    df.at[idx, "sub_phase_tag"] = "OT-3 Support consolidation"
                else:
                    df.at[idx, "sub_phase_tag"] = "OT-5 Transition reset"
            else:
                df.at[idx, "tactical_phase"] = "Offensive Moment"
                x = float(row.get("x", 0) or 0)
                if x < 35:
                    df.at[idx, "sub_phase_tag"] = "OM-1 First-phase circulation"
                elif x < 67:
                    df.at[idx, "sub_phase_tag"] = "OM-3 Pre-final-third stabilization"
                elif row.get("is_shot", False):
                    df.at[idx, "sub_phase_tag"] = "OM-5 Box access and shot setup"
                elif row.get("is_pass", False):
                    df.at[idx, "sub_phase_tag"] = "OM-4 Final-third entry attempt"
                else:
                    df.at[idx, "sub_phase_tag"] = "OM-2 Pressure escape progression"
        else:
            # Defensive side: DT vs DM
            if seq is not None and seq.get("duration_s", 999) <= 10 and seq.get("is_regain", False):
                df.at[idx, "tactical_phase"] = "Defensive Transition"
                x = float(row.get("x", 0) or 0)
                if row.get("type_id") in {7, 8, 49}:
                    df.at[idx, "sub_phase_tag"] = "DT-2 Counterpress engagement"
                elif x >= 67:
                    df.at[idx, "sub_phase_tag"] = "DT-1 Immediate reaction window"
                elif x < 33:
                    df.at[idx, "sub_phase_tag"] = "DT-5 Emergency retreat"
                else:
                    df.at[idx, "sub_phase_tag"] = "DT-3 Recovery block formation"
            else:
                df.at[idx, "tactical_phase"] = "Defensive Moment"
                x = float(row.get("x", 0) or 0)
                if x >= 67:
                    df.at[idx, "sub_phase_tag"] = "DM-1 High press wave"
                elif x >= 40:
                    df.at[idx, "sub_phase_tag"] = "DM-2 Mid-block containment"
                elif row.get("type_id") in {10, 15}:
                    df.at[idx, "sub_phase_tag"] = "DM-4 Box defense episode"
                else:
                    df.at[idx, "sub_phase_tag"] = "DM-3 Low-block protection"

    return df
