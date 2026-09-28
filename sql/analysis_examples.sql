-- 1. Segment performance using joins and conditional aggregation.
SELECT
    f.month,
    c.segment,
    c.plan,
    COUNT(DISTINCT f.customer_id) AS customers,
    ROUND(SUM(f.mrr), 2) AS mrr,
    ROUND(AVG(f.feature_adoption_rate), 3) AS adoption_rate,
    ROUND(AVG(f.nps), 1) AS avg_nps,
    SUM(CASE WHEN f.churn_flag = 1 THEN 1 ELSE 0 END) AS churned_customers
FROM fact_customer_month AS f
JOIN dim_customer AS c USING (customer_id)
GROUP BY f.month, c.segment, c.plan;

-- 2. Accounts whose support burden is above their segment average.
WITH latest AS (
    SELECT f.*,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY month DESC) AS row_num
    FROM fact_customer_month AS f
), segment_benchmark AS (
    SELECT c.segment, AVG(l.support_tickets) AS avg_tickets
    FROM latest AS l
    JOIN dim_customer AS c USING (customer_id)
    WHERE l.row_num = 1
    GROUP BY c.segment
)
SELECT l.customer_id, c.segment, c.plan, l.support_tickets, b.avg_tickets, l.nps, l.mrr
FROM latest AS l
JOIN dim_customer AS c USING (customer_id)
JOIN segment_benchmark AS b ON b.segment = c.segment
WHERE l.row_num = 1 AND l.support_tickets > b.avg_tickets
ORDER BY l.support_tickets DESC, l.mrr DESC;

-- 3. Rolling three-month MRR and month-over-month growth.
SELECT
    month,
    monthly_mrr,
    ROUND(AVG(monthly_mrr) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_3m_mrr,
    ROUND((monthly_mrr - LAG(monthly_mrr) OVER (ORDER BY month)) /
          NULLIF(LAG(monthly_mrr) OVER (ORDER BY month), 0), 4) AS mom_growth
FROM (
    SELECT month, SUM(mrr) AS monthly_mrr
    FROM fact_customer_month
    GROUP BY month
)
ORDER BY month;

