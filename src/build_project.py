from __future__ import annotations

import csv
import json
import math
import random
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_DIR = ROOT / "database"
ARTIFACT_DIR = ROOT / "artifacts"
DASHBOARD_DIR = ROOT / "dashboard"


def month_start(year: int, month: int, offset: int) -> date:
    index = year * 12 + month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -30, 30)
    return 1.0 / (1.0 + np.exp(-clipped))


def generate_data(customer_count: int = 1200, months: int = 18) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = random.Random(SEED)
    np_rng = np.random.default_rng(SEED)
    plans = {
        "Starter": {"price": 19, "seat_mean": 6},
        "Growth": {"price": 49, "seat_mean": 16},
        "Enterprise": {"price": 89, "seat_mean": 42},
    }
    regions = ["India", "North America", "Europe", "APAC"]
    channels = ["Organic", "Partner", "Paid Search", "Outbound"]
    segments = ["SMB", "Mid-Market", "Enterprise"]
    customers: list[dict] = []
    monthly: list[dict] = []

    for customer_number in range(1, customer_count + 1):
        customer_id = f"C{customer_number:05d}"
        segment = rng.choices(segments, weights=[0.55, 0.30, 0.15])[0]
        plan = rng.choices(
            list(plans),
            weights={"SMB": [0.72, 0.25, 0.03], "Mid-Market": [0.18, 0.65, 0.17], "Enterprise": [0.03, 0.27, 0.70]}[segment],
        )[0]
        region = rng.choices(regions, weights=[0.42, 0.24, 0.20, 0.14])[0]
        channel = rng.choices(channels, weights=[0.34, 0.20, 0.28, 0.18])[0]
        signup_offset = rng.randint(0, 5)
        signup = month_start(2025, 1, signup_offset)
        base_seats = max(2, int(np_rng.normal(plans[plan]["seat_mean"], plans[plan]["seat_mean"] * 0.25)))
        health = float(np_rng.normal(0, 1))
        churned = False
        customers.append(
            {
                "customer_id": customer_id,
                "company_name": f"Nimbus Customer {customer_number:04d}",
                "segment": segment,
                "plan": plan,
                "region": region,
                "acquisition_channel": channel,
                "signup_date": signup.isoformat(),
            }
        )

        for month_index in range(signup_offset, months):
            if churned:
                break
            period = month_start(2025, 1, month_index)
            tenure = month_index - signup_offset + 1
            seasonal = 1.0 + 0.08 * math.sin((month_index + 1) * math.pi / 6)
            active_seats = max(1, int(base_seats * seasonal + np_rng.normal(0, max(1, base_seats * 0.06))))
            logins = max(1, int(active_seats * np_rng.normal(8.5 + health, 1.8)))
            feature_adoption = float(np.clip(np_rng.normal(0.58 + health * 0.09 + tenure * 0.006, 0.14), 0.05, 0.98))
            support_tickets = max(0, int(np_rng.poisson(max(0.2, active_seats / 18 - health * 0.35))))
            avg_resolution_hours = float(max(1.5, np_rng.normal(15 + support_tickets * 1.7 - health * 2.5, 4.5)))
            nps = int(np.clip(np_rng.normal(42 + health * 15 + feature_adoption * 18 - support_tickets * 2.2, 14), -40, 100))
            revenue = round(active_seats * plans[plan]["price"], 2)
            discount = rng.choices([0.0, 0.05, 0.10, 0.15], weights=[0.62, 0.20, 0.13, 0.05])[0]
            mrr = round(revenue * (1 - discount), 2)
            prior_mrr = monthly[-1]["mrr"] if monthly and monthly[-1]["customer_id"] == customer_id else mrr
            expansion_mrr = round(max(0, mrr - prior_mrr), 2)
            contraction_mrr = round(max(0, prior_mrr - mrr), 2)
            risk_logit = (
                -2.7
                - 1.7 * feature_adoption
                - 0.018 * nps
                + 0.13 * support_tickets
                + 0.018 * avg_resolution_hours
                + (0.55 if channel == "Paid Search" else 0)
                + (0.40 if tenure <= 3 else 0)
                - 0.25 * health
            )
            churn_probability = 1 / (1 + math.exp(-risk_logit))
            churn_flag = int(tenure >= 2 and rng.random() < churn_probability)
            monthly.append(
                {
                    "customer_id": customer_id,
                    "month": period.isoformat(),
                    "tenure_months": tenure,
                    "active_seats": active_seats,
                    "monthly_logins": logins,
                    "feature_adoption_rate": round(feature_adoption, 4),
                    "support_tickets": support_tickets,
                    "avg_resolution_hours": round(avg_resolution_hours, 2),
                    "nps": nps,
                    "gross_revenue": revenue,
                    "discount_rate": discount,
                    "mrr": mrr,
                    "expansion_mrr": expansion_mrr,
                    "contraction_mrr": contraction_mrr,
                    "churn_flag": churn_flag,
                }
            )
            churned = bool(churn_flag)

    return pd.DataFrame(customers), pd.DataFrame(monthly)


def validate(customers: pd.DataFrame, monthly: pd.DataFrame) -> None:
    if customers["customer_id"].duplicated().any():
        raise ValueError("Duplicate customer IDs")
    if monthly.duplicated(["customer_id", "month"]).any():
        raise ValueError("Duplicate customer-month rows")
    if not monthly["customer_id"].isin(customers["customer_id"]).all():
        raise ValueError("Unknown customer in monthly fact")
    if not monthly["feature_adoption_rate"].between(0, 1).all():
        raise ValueError("Feature adoption is outside 0-1")
    if not monthly["discount_rate"].between(0, 1).all():
        raise ValueError("Discount rate is outside 0-1")
    if (monthly[["mrr", "active_seats", "monthly_logins"]] < 0).any().any():
        raise ValueError("Negative commercial or usage measure")


def create_warehouse(customers: pd.DataFrame, monthly: pd.DataFrame) -> Path:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db_path = DB_DIR / "saas_intelligence.db"
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as connection:
        connection.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        customers.to_sql("dim_customer", connection, if_exists="append", index=False)
        monthly.to_sql("fact_customer_month", connection, if_exists="append", index=False)
        connection.execute("ANALYZE")
    return db_path


@dataclass
class ModelResult:
    metrics: dict[str, float]
    scores: pd.DataFrame
    coefficients: pd.DataFrame


def train_churn_model(customers: pd.DataFrame, monthly: pd.DataFrame) -> ModelResult:
    feature_names = [
        "tenure_months",
        "active_seats",
        "monthly_logins",
        "feature_adoption_rate",
        "support_tickets",
        "avg_resolution_hours",
        "nps",
        "discount_rate",
        "contraction_mrr",
    ]
    model_frame = monthly.merge(customers[["customer_id", "segment", "plan", "region"]], on="customer_id", how="left")
    ordered_months = sorted(model_frame["month"].unique())
    split_month = ordered_months[-4]
    train = model_frame[model_frame["month"] < split_month].copy()
    test = model_frame[model_frame["month"] >= split_month].copy()
    x_train = train[feature_names].to_numpy(dtype=float)
    y_train = train["churn_flag"].to_numpy(dtype=float)
    x_test = test[feature_names].to_numpy(dtype=float)
    y_test = test["churn_flag"].to_numpy(dtype=float)
    means = x_train.mean(axis=0)
    scales = x_train.std(axis=0)
    scales[scales == 0] = 1
    x_train = (x_train - means) / scales
    x_test_scaled = (x_test - means) / scales
    x_train = np.c_[np.ones(len(x_train)), x_train]
    x_test_scaled = np.c_[np.ones(len(x_test_scaled)), x_test_scaled]
    weights = np.zeros(x_train.shape[1])
    positive_weight = max(1.0, (len(y_train) - y_train.sum()) / max(1.0, y_train.sum()))
    learning_rate = 0.04
    for _ in range(1400):
        probabilities = sigmoid(x_train @ weights)
        row_weights = np.where(y_train == 1, positive_weight, 1.0)
        gradient = (x_train.T @ ((probabilities - y_train) * row_weights)) / row_weights.sum()
        gradient[1:] += 0.002 * weights[1:]
        weights -= learning_rate * gradient
    train_probabilities = sigmoid(x_train @ weights)
    best_threshold = 0.5
    best_train_f1 = -1.0
    for threshold in np.arange(0.20, 0.81, 0.02):
        train_predictions = (train_probabilities >= threshold).astype(int)
        train_tp = int(((train_predictions == 1) & (y_train == 1)).sum())
        train_fp = int(((train_predictions == 1) & (y_train == 0)).sum())
        train_fn = int(((train_predictions == 0) & (y_train == 1)).sum())
        train_precision = train_tp / max(1, train_tp + train_fp)
        train_recall = train_tp / max(1, train_tp + train_fn)
        train_f1 = 2 * train_precision * train_recall / max(1e-9, train_precision + train_recall)
        if train_f1 > best_train_f1:
            best_train_f1 = train_f1
            best_threshold = float(threshold)
    probabilities = sigmoid(x_test_scaled @ weights)
    predictions = (probabilities >= best_threshold).astype(int)
    tp = int(((predictions == 1) & (y_test == 1)).sum())
    tn = int(((predictions == 0) & (y_test == 0)).sum())
    fp = int(((predictions == 1) & (y_test == 0)).sum())
    fn = int(((predictions == 0) & (y_test == 1)).sum())
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-9, precision + recall)
    accuracy = (tp + tn) / max(1, len(y_test))
    order = np.argsort(-probabilities)
    positives = y_test.sum()
    negatives = len(y_test) - positives
    if positives and negatives:
        ranks = np.empty_like(order)
        ranks[order] = np.arange(len(order))
        positive_rank_sum = ranks[y_test == 1].sum()
        auc = 1 - (positive_rank_sum - positives * (positives - 1) / 2) / (positives * negatives)
    else:
        auc = 0.5
    metrics = {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "split_month": split_month,
        "decision_threshold": round(best_threshold, 2),
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(auc), 4),
        "test_churn_rate": round(float(y_test.mean()), 4),
    }
    latest = model_frame.sort_values("month").groupby("customer_id", as_index=False).tail(1).copy()
    latest_x = (latest[feature_names].to_numpy(dtype=float) - means) / scales
    latest["churn_probability"] = sigmoid(np.c_[np.ones(len(latest_x)), latest_x] @ weights)
    latest["risk_band"] = pd.cut(
        latest["churn_probability"],
        bins=[-0.001, 0.30, 0.55, 1.0],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    latest["recommended_action"] = latest["risk_band"].map(
        {
            "High": "Executive outreach and adoption recovery plan",
            "Medium": "Customer-success review within 14 days",
            "Low": "Monitor through standard success cadence",
        }
    )
    scores = latest[
        ["customer_id", "month", "segment", "plan", "region", "mrr", "churn_flag", "churn_probability", "risk_band", "recommended_action"]
    ].copy()
    scores["churn_probability"] = scores["churn_probability"].round(4)
    coefficients = pd.DataFrame({"feature": ["intercept", *feature_names], "standardized_coefficient": weights.round(5)})
    return ModelResult(metrics=metrics, scores=scores, coefficients=coefficients)


def write_outputs(customers: pd.DataFrame, monthly: pd.DataFrame, db_path: Path, model: ModelResult) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    customers.to_csv(DATA_DIR / "dim_customer.csv", index=False)
    monthly.to_csv(DATA_DIR / "fact_customer_month.csv", index=False)
    powerbi = monthly.merge(customers, on="customer_id", how="left")
    powerbi.to_csv(DATA_DIR / "powerbi_customer_month.csv", index=False)
    model.scores.to_csv(DATA_DIR / "customer_risk_scores.csv", index=False)
    model.coefficients.to_csv(ARTIFACT_DIR / "model_coefficients.csv", index=False)
    (ARTIFACT_DIR / "model_metrics.json").write_text(json.dumps(model.metrics, indent=2), encoding="utf-8")
    with sqlite3.connect(db_path) as connection:
        model.scores.to_sql("customer_risk_score", connection, if_exists="replace", index=False)
        query = (ROOT / "sql" / "kpi_queries.sql").read_text(encoding="utf-8")
        kpis = pd.read_sql_query(query, connection)
    kpis.to_csv(ARTIFACT_DIR / "kpi_snapshot.csv", index=False)
    build_dashboard(powerbi, model.metrics, model.scores)


def build_dashboard(powerbi: pd.DataFrame, metrics: dict[str, float], scores: pd.DataFrame) -> None:
    aggregate = (
        powerbi.groupby(["month", "region", "segment", "plan"], as_index=False)
        .agg(
            mrr=("mrr", "sum"),
            active_customers=("customer_id", "nunique"),
            churned_customers=("churn_flag", "sum"),
            avg_nps=("nps", "mean"),
            adoption=("feature_adoption_rate", "mean"),
            support_tickets=("support_tickets", "sum"),
            expansion_mrr=("expansion_mrr", "sum"),
            contraction_mrr=("contraction_mrr", "sum"),
        )
        .round(4)
    )
    template = (Path(__file__).with_name("dashboard_template.html")).read_text(encoding="utf-8")
    html = (
        template.replace("__AGGREGATE_DATA__", json.dumps(aggregate.to_dict(orient="records"), separators=(",", ":")))
        .replace("__RISK_DATA__", json.dumps(scores.to_dict(orient="records"), separators=(",", ":")))
        .replace("__MODEL_METRICS__", json.dumps(metrics, separators=(",", ":")))
    )
    (DASHBOARD_DIR / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    customers, monthly = generate_data()
    validate(customers, monthly)
    db_path = create_warehouse(customers, monthly)
    model = train_churn_model(customers, monthly)
    write_outputs(customers, monthly, db_path, model)
    print(json.dumps({"customers": len(customers), "customer_months": len(monthly), **model.metrics}, indent=2))


if __name__ == "__main__":
    main()

