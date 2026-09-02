"""Tests for analytics/rfm.py."""

from analytics.rfm import compute_rfm, format_rfm_summary


def test_compute_rfm_shape(sample_orders):
    rfm = compute_rfm(sample_orders)
    assert "customer_id" in rfm.columns
    assert "segment" in rfm.columns
    assert len(rfm) == sample_orders["customer_id"].nunique()


def test_rfm_scores_range(sample_orders):
    rfm = compute_rfm(sample_orders, n_segments=4)
    for col in ["r_score", "f_score", "m_score"]:
        assert rfm[col].between(1, 4).all(), f"{col} out of [1, 4]"


def test_rfm_segments_are_known_labels(sample_orders):
    rfm = compute_rfm(sample_orders)
    valid = {"Champions", "Loyal Customers", "At Risk", "Lost"}
    assert set(rfm["segment"].unique()).issubset(valid)


def test_format_rfm_summary_under_2000(sample_orders):
    rfm = compute_rfm(sample_orders)
    summary = format_rfm_summary(rfm)
    assert len(summary) <= 2000
    assert "customers" in summary.lower()
