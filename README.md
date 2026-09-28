# SaaS Revenue & Churn Intelligence

Portfolio project aligned to a Business Intelligence Engineer / Data Scientist role in the software-product industry.

## Business question

Which customer segments drive recurring revenue, where is churn risk rising, and which accounts should Customer Success prioritize?

## What this project demonstrates

- **Python:** deterministic data generation, validation, feature engineering, automation, and a from-scratch logistic-regression churn model.
- **SQL:** star-style warehouse tables, joins, window functions, CTEs, subqueries, aggregations, and query indexes.
- **Power BI:** import-ready analytical view, relationship model, DAX measures, slicers, KPI definitions, and a three-page dashboard plan.
- **Data science:** leakage-aware customer features, chronological train/test split, standardized features, classification metrics, and scored customer risk.

## Architecture

```text
Synthetic SaaS events -> Python validation/feature engineering -> SQLite warehouse
                                                          |-> SQL KPI extracts
                                                          |-> churn model + risk scores
                                                          `-> Power BI export + dashboard preview
```

## Run locally

```powershell
python src/build_project.py
python -m unittest discover -s tests -v
```

The script recreates all generated artifacts using seed `42`.

## Key outputs

- `database/saas_intelligence.db` - SQLite warehouse.
- `data/powerbi_customer_month.csv` - Power BI fact export.
- `data/customer_risk_scores.csv` - account-level churn scores and priority bands.
- `artifacts/model_metrics.json` - holdout model metrics.
- `artifacts/kpi_snapshot.csv` - executive KPI snapshot produced by SQL.
- `dashboard/index.html` - browser preview of the intended Power BI experience.
- `powerbi/POWER_BI_BUILD_GUIDE.md` and `powerbi/measures.dax` - report construction assets.

## Data model

- `dim_customer`: one row per customer, including plan, segment, region, acquisition channel, and signup date.
- `fact_customer_month`: one row per customer-month with seats, usage, support, NPS, revenue, and churn label.
- `customer_risk_score`: scored active/latest customer records with probability and action band.

## Validation boundary

The data is synthetic and intentionally contains no real customer information. The SQLite pipeline, SQL extracts, tests, and browser preview are locally generated and verified. The included Power BI assets are import-ready; a native `.pbix` is not claimed unless the report is actually built and saved in Power BI.

## Related Power BI portfolio

An existing public Power BI and SQL portfolio is available at `github.com/ashu-94/POWER_BI_DASHBOARD_SQL_PROJECTS_OCTOBER`. The repository includes Power BI Capstone, Student Survey, and YouTube Capstone PBIX artifacts, a Student Survey PDF export, and SQL exercises.

