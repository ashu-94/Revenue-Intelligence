PRAGMA foreign_keys = ON;

CREATE TABLE dim_customer (
    customer_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    segment TEXT NOT NULL,
    plan TEXT NOT NULL,
    region TEXT NOT NULL,
    acquisition_channel TEXT NOT NULL,
    signup_date TEXT NOT NULL
);

CREATE TABLE fact_customer_month (
    customer_id TEXT NOT NULL,
    month TEXT NOT NULL,
    tenure_months INTEGER NOT NULL CHECK (tenure_months > 0),
    active_seats INTEGER NOT NULL CHECK (active_seats > 0),
    monthly_logins INTEGER NOT NULL CHECK (monthly_logins >= 0),
    feature_adoption_rate REAL NOT NULL CHECK (feature_adoption_rate BETWEEN 0 AND 1),
    support_tickets INTEGER NOT NULL CHECK (support_tickets >= 0),
    avg_resolution_hours REAL NOT NULL CHECK (avg_resolution_hours >= 0),
    nps INTEGER NOT NULL CHECK (nps BETWEEN -100 AND 100),
    gross_revenue REAL NOT NULL CHECK (gross_revenue >= 0),
    discount_rate REAL NOT NULL CHECK (discount_rate BETWEEN 0 AND 1),
    mrr REAL NOT NULL CHECK (mrr >= 0),
    expansion_mrr REAL NOT NULL CHECK (expansion_mrr >= 0),
    contraction_mrr REAL NOT NULL CHECK (contraction_mrr >= 0),
    churn_flag INTEGER NOT NULL CHECK (churn_flag IN (0, 1)),
    PRIMARY KEY (customer_id, month),
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id)
);

CREATE INDEX idx_fact_month ON fact_customer_month(month);
CREATE INDEX idx_fact_churn_month ON fact_customer_month(churn_flag, month);
CREATE INDEX idx_customer_segment_plan ON dim_customer(segment, plan);

