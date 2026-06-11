"""Parallel tactical intelligence overlay pipeline (non-destructive)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .feature_flags import get_feature_flag_map
from .kpi_extensions import build_cross_phase_metrics, build_kpi_extension_tables
from .sequence_enrichment import enrich_sequences
from .sub_phases import tag_sub_phases


@dataclass
class OverlayOutput:
    sub_phase_events: pd.DataFrame
    kpi_extension_tables: dict[str, pd.DataFrame]
    cross_phase_metrics: pd.DataFrame
    sequence_enrichment_layer: pd.DataFrame
    feature_flags: dict[str, bool]


def build_tactical_intelligence_overlay(events: pd.DataFrame, team_id: str, opp_id: str) -> OverlayOutput:
    """Build additive tactical intelligence outputs from event data.

    This function does not mutate baseline tables and can be skipped safely.
    """
    flags = get_feature_flag_map()

    # If all flags are off, return empty additive structures.
    if not any(flags.values()):
        return OverlayOutput(
            sub_phase_events=pd.DataFrame(),
            kpi_extension_tables={},
            cross_phase_metrics=pd.DataFrame(),
            sequence_enrichment_layer=pd.DataFrame(),
            feature_flags=flags,
        )

    events_seq, seq_layer = enrich_sequences(events) if flags["ENABLE_SEQUENCE_ENRICHMENT"] else (events.copy(), pd.DataFrame())

    if flags["ENABLE_SUB_PHASE_TAGGING"]:
        tagged = tag_sub_phases(events_seq, seq_layer, team_id=team_id, opp_id=opp_id)
    else:
        tagged = events_seq.copy()

    kpi_tables = {}
    if flags["ENABLE_ADVANCED_KPI_LAYER"]:
        kpi_tables = build_kpi_extension_tables(tagged, seq_layer, team_id=team_id, opp_id=opp_id)

    cross_phase = pd.DataFrame()
    if flags["ENABLE_CROSS_PHASE_METRICS"]:
        cross_phase = build_cross_phase_metrics(tagged, team_id=team_id)

    return OverlayOutput(
        sub_phase_events=tagged,
        kpi_extension_tables=kpi_tables,
        cross_phase_metrics=cross_phase,
        sequence_enrichment_layer=seq_layer,
        feature_flags=flags,
    )
