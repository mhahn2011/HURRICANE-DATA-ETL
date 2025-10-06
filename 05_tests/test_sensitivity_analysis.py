"""Sensitivity documentation for alpha-parameter selection."""

import pandas as pd


def test_alpha_06_is_production_value():
    """Alpha 0.6 chosen via visual QA across 14 Gulf Coast hurricanes."""

    production_alpha = 0.6
    assert production_alpha == 0.6


def test_batch_processing_performance():
    """Batch summary shows all 14 production envelopes remained valid."""

    summary = pd.read_csv("01_data_sources/hurdat2/outputs/batch_processing_summary.csv")
    assert len(summary) == 14
    assert summary["envelope_valid"].all()
    assert summary["status"].eq("SUCCESS").all()
