-- 01_build_fct_orders.sql
--
-- stg_delivered_orders : every order with status 'delivered', all stage durations computed,
--                        plus a dq_issue column (NULL = clean). Used by 02_data_quality_checks.sql.
-- fct_orders           : one row per CLEAN delivered order (dq_issue IS NULL). Used for all KPIs.
--
-- Decisions
--   * Durations are fractional days: (epoch(b) - epoch(a)) / 86400.
--     (DuckDB date_diff('day', ...) counts midnight boundaries, so 23:00 -> 01:00 would be "1 day".)
--   * Lateness is judged at DATE level: the estimate is a date (00:00:00), so an order delivered
--     any time on the estimated day is on time.
--   * ~2% of orders contain items from >1 seller. seller_state = state of the seller of
--     order_item_id = 1; n_sellers is kept so these orders can be filtered out if needed.

CREATE OR REPLACE TABLE stg_delivered_orders AS
WITH first_seller AS (
    SELECT i.order_id, s.seller_state
    FROM raw_order_items i
    JOIN raw_sellers s USING (seller_id)
    WHERE i.order_item_id = 1
),
seller_counts AS (
    SELECT order_id, COUNT(DISTINCT seller_id) AS n_sellers
    FROM raw_order_items
    GROUP BY order_id
),
base AS (
    SELECT
        o.order_id,
        o.customer_id,
        c.customer_state,
        fs.seller_state,
        sc.n_sellers,
        o.order_purchase_timestamp                    AS purchase_ts,
        o.order_delivered_carrier_date                AS carrier_ts,
        o.order_delivered_customer_date               AS delivered_ts,
        CAST(o.order_estimated_delivery_date AS DATE) AS estimated_date
    FROM raw_orders o
    JOIN raw_customers c USING (customer_id)
    LEFT JOIN first_seller fs USING (order_id)
    LEFT JOIN seller_counts sc USING (order_id)
    WHERE o.order_status = 'delivered'
),
calc AS (
    SELECT
        *,
        ROUND((epoch(carrier_ts)   - epoch(purchase_ts)) / 86400.0, 2) AS handling_days,
        ROUND((epoch(delivered_ts) - epoch(carrier_ts))  / 86400.0, 2) AS transit_days,
        ROUND((epoch(delivered_ts) - epoch(purchase_ts)) / 86400.0, 2) AS total_lead_days,
        date_diff('day', estimated_date, CAST(delivered_ts AS DATE))  AS delay_days
    FROM base
)
SELECT
    *,
    CASE
        WHEN delivered_ts IS NULL OR carrier_ts IS NULL     THEN 'missing_timestamp'
        WHEN delivered_ts < carrier_ts                      THEN 'delivered_before_shipped'
        WHEN carrier_ts < purchase_ts                       THEN 'shipped_before_purchase'
        WHEN total_lead_days < 0 OR total_lead_days > 100   THEN 'lead_time_outlier'
    END AS dq_issue
FROM calc;

CREATE OR REPLACE TABLE fct_orders AS
SELECT
    order_id,
    customer_id,
    CAST(date_trunc('month', purchase_ts) AS DATE) AS purchase_month,
    purchase_ts,
    carrier_ts,
    delivered_ts,
    estimated_date,
    customer_state,
    seller_state,
    n_sellers,
    customer_state <> seller_state                 AS is_cross_state,
    handling_days,
    transit_days,
    total_lead_days,
    delay_days,
    delay_days > 0                                 AS is_late
FROM stg_delivered_orders
WHERE dq_issue IS NULL;

-- fct_orders row count
SELECT COUNT(*) AS n_rows FROM fct_orders;
