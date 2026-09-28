# Power BI build guide

## Import

1. Import `data/powerbi_customer_month.csv` as `powerbi_customer_month`.
2. Import `data/customer_risk_scores.csv` as `customer_risk_scores`.
3. Set `month` to Date, monetary columns to Fixed decimal number, and rates/probabilities to Decimal number.
4. Create a calendar table and mark it as the date table:

```DAX
Calendar = CALENDAR(MIN(powerbi_customer_month[month]), MAX(powerbi_customer_month[month]))
```

5. Relate `Calendar[Date]` (1) to `powerbi_customer_month[month]` (*).
6. Relate `customer_risk_scores[customer_id]` (1) to `powerbi_customer_month[customer_id]` (*) with single-direction filtering.

## Measures

Create the measures in `measures.dax`. Format MRR measures as currency, rates as percentages, and NPS as a one-decimal number.

## Page 1 - Executive Overview

- KPI cards: Total MRR, Active Customers, Customer Churn Rate, Net Revenue Retention, Average NPS.
- Combo chart: Total MRR as columns and MRR Growth Rate as a line by month.
- Stacked bar: MRR by segment and plan.
- Line chart: Customer Churn Rate and Feature Adoption by month.
- Slicers: month, region, segment, plan, acquisition channel.

## Page 2 - Customer Health

- Scatter plot: Feature Adoption (x), Average NPS (y), MRR (size), segment (legend).
- Matrix: region -> segment -> plan with MRR, churn, support tickets, and resolution time.
- Decomposition tree: Customer Churn Rate explained by plan, channel, segment, and region.
- Tooltip page: customer ID, MRR, support tickets, NPS, adoption, churn probability.

## Page 3 - Retention Action Center

- Card: Revenue at Risk.
- Donut: customers by risk band.
- Table: customer ID, segment, plan, MRR, churn probability, recommended action.
- Conditional formatting: red for High, amber for Medium, green for Low.
- Drill-through filter: customer ID.

## Design system

- Canvas: 16:9, off-white background `#F2F5FA`.
- Primary: navy `#0B1930`; accent: blue `#2563EB`; highlight: cyan `#06B6D4`; risk: red `#E44747`.
- Use a consistent 12-column grid, 16 px gaps, short titles, and visible units.

## Verification checklist

- Confirm the latest-month MRR, active customers, churn rate, NRR, and NPS match `artifacts/kpi_snapshot.csv`.
- Check each slicer affects all intended visuals.
- Test the customer drill-through and tooltip.
- Verify percentage and currency formatting, titles, clipping, and empty states.
- Save the report only after the reconciliation passes.

