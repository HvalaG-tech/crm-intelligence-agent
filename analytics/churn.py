"""Churn prediction — feature engineering + sklearn pipeline.

Note on Olist data: ~90% of customers buy only once (marketplace behaviour).
The inactivity threshold must be ≥365 days to avoid labelling normal
single-purchase behaviour as churn.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["total_orders", "total_revenue", "avg_order_value", "tenure_days", "recency_days"]
DEFAULT_INACTIVITY_DAYS = 365


class ChurnModel:
    def score(self, customers: pd.DataFrame, inactivity_days: int = DEFAULT_INACTIVITY_DAYS) -> pd.DataFrame:
        """Return customers DataFrame enriched with churn_score and churn_label.

        Args:
            customers: customers_enriched DataFrame.
            inactivity_days: Days without purchase to label as churned. Min 365 for Olist.

        Returns:
            DataFrame sorted by churn_score descending.
        """
        df = customers.copy()
        ref_date = df["last_purchase"].max()

        df["recency_days"] = (ref_date - df["last_purchase"]).dt.days
        df["tenure_days"] = (df["last_purchase"] - df["first_purchase"]).dt.days.clip(lower=0)
        df["churned"] = (df["recency_days"] >= inactivity_days).astype(int)

        feature_df = df[FEATURES].fillna(0)
        labels = df["churned"]

        # Edge case: single class or too few samples
        if labels.nunique() < 2 or len(df) < 20:
            df["churn_score"] = labels.astype(float)
            df["churn_label"] = labels.map({1: "High Risk", 0: "Low Risk"})
            return df.sort_values("churn_score", ascending=False)

        # Train on 80% to avoid overfitting on the scoring set
        X_train, _, y_train, _ = train_test_split(
            feature_df, labels, test_size=0.2, random_state=42, stratify=labels
        )

        clf = Pipeline([
            ("scaler", StandardScaler()),
            # class_weight='balanced' compensates for heavy class imbalance in Olist
            ("clf", RandomForestClassifier(
                n_estimators=100, random_state=42, n_jobs=-1, class_weight="balanced"
            )),
        ])
        clf.fit(X_train, y_train)

        proba = clf.predict_proba(feature_df)
        if proba.shape[1] == 1:
            only_class = clf.classes_[0]
            df["churn_score"] = proba[:, 0] if only_class == 1 else 1 - proba[:, 0]
        else:
            df["churn_score"] = proba[:, 1]

        df["churn_label"] = (df["churn_score"] >= 0.5).map({True: "High Risk", False: "Low Risk"})

        return df.sort_values("churn_score", ascending=False)


def format_churn_summary(scored: pd.DataFrame, top_n: int = 20) -> str:
    high_risk = (scored["churn_score"] >= 0.5).sum()
    total = len(scored)
    top = scored.head(top_n)[["customer_id", "churn_score", "recency_days", "total_revenue"]]

    lines = [
        f"Churn Analysis — {total:,} customers scored (seuil inactivité : 365 jours):",
        f"  High risk (score ≥ 0.5): {high_risk:,} customers ({high_risk/total*100:.1f}%)",
        f"  Low risk: {total-high_risk:,} customers",
        f"\nTop {top_n} highest-risk customers:",
        top.to_string(index=False, float_format=lambda x: f"{x:.2f}"),
    ]
    return "\n".join(lines)
