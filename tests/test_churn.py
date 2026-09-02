"""Tests for analytics/churn.py."""

from analytics.churn import ChurnModel, format_churn_summary


def test_churn_score_range(sample_customers):
    model = ChurnModel()
    scored = model.score(sample_customers, inactivity_days=180)
    assert "churn_score" in scored.columns
    assert scored["churn_score"].between(0, 1).all()


def test_churn_sorted_descending(sample_customers):
    model = ChurnModel()
    scored = model.score(sample_customers)
    assert list(scored["churn_score"]) == sorted(scored["churn_score"], reverse=True)


def test_format_churn_summary_under_2000(sample_customers):
    model = ChurnModel()
    scored = model.score(sample_customers)
    summary = format_churn_summary(scored, top_n=5)
    assert len(summary) <= 2000
