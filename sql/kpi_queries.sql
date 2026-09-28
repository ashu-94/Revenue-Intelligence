WITH monthly AS (
    SELECT
        month,
        SUM(mrr) AS mrr,
        COUNT(DISTINCT customer_id) AS active_customers,
        SUM(churn_flag) AS churned_customers,
        AVG(nps) AS avg_nps,
        SUM(expansion_mrr) AS expansion_mrr,
        SUM(contraction_mrr) AS contraction_mrr
    FROM fact_customer_month
    GROUP BY month
), lagged AS (
    SELECT
        *,
        LAG(mrr) OVER (ORDER BY month) AS prior_mrr,
        LAG(active_customers) OVER (ORDER BY month) AS prior_customers
    FROM monthly
)
SELECT
    month,
    ROUND(mrr, 2) AS mrr,
    active_customers,
    churned_customers,
    ROUND(CAST(churned_customers AS REAL) / NULLIF(active_customers, 0), 4) AS churn_rate,
    ROUND(avg_nps, 2) AS avg_nps,
    ROUND(expansion_mrr, 2) AS expansion_mrr,
    ROUND(contraction_mrr, 2) AS contraction_mrr,
    ROUND((COALESCE(prior_mrr, mrr) + expansion_mrr - contraction_mrr) / NULLIF(COALESCE(prior_mrr, mrr), 0), 4) AS net_revenue_retention,
    ROUND((mrr - prior_mrr) / NULLIF(prior_mrr, 0), 4) AS mrr_growth_rate
FROM lagged
ORDER BY month;

