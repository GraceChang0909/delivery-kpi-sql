-- 03_kpi_analysis.sql
-- All KPIs read from fct_orders. Definitions: agent/metric_definitions.md
-- Each query is saved as a kpi_* view so the notebook / Tableau export can read it by name.

-- KPI1 monthly on-time delivery rate (purchase month, 2017-01 to 2018-08; other months have < 300 orders)
CREATE OR REPLACE VIEW kpi1_monthly_ontime AS
SELECT purchase_month,
       COUNT(*)                                            AS n_orders,
       ROUND(100.0 * AVG(CASE WHEN is_late THEN 0 ELSE 1 END), 2) AS on_time_rate_pct
FROM fct_orders
WHERE purchase_month BETWEEN DATE '2017-01-01' AND DATE '2018-08-01'
GROUP BY purchase_month
ORDER BY purchase_month;
SELECT * FROM kpi1_monthly_ontime;

-- KPI2 average lead time breakdown: handling (purchase -> carrier) vs transit (carrier -> customer)
CREATE OR REPLACE VIEW kpi2_lead_time_breakdown AS
SELECT 'handling' AS stage, ROUND(AVG(handling_days), 2) AS avg_days, ROUND(MEDIAN(handling_days), 2) AS median_days,
       ROUND(100.0 * AVG(handling_days) / AVG(total_lead_days), 1) AS share_of_total_pct
FROM fct_orders
UNION ALL
SELECT 'transit', ROUND(AVG(transit_days), 2), ROUND(MEDIAN(transit_days), 2),
       ROUND(100.0 * AVG(transit_days) / AVG(total_lead_days), 1)
FROM fct_orders
UNION ALL
SELECT 'total', ROUND(AVG(total_lead_days), 2), ROUND(MEDIAN(total_lead_days), 2), 100.0
FROM fct_orders;
SELECT * FROM kpi2_lead_time_breakdown;

-- KPI3 5 worst customer states by on-time rate (states with >= 100 orders)
CREATE OR REPLACE VIEW kpi3_state_ontime AS
SELECT customer_state,
       COUNT(*)                                            AS n_orders,
       ROUND(100.0 * AVG(CASE WHEN is_late THEN 0 ELSE 1 END), 2) AS on_time_rate_pct,
       ROUND(AVG(handling_days), 2)                        AS avg_handling_days,
       ROUND(AVG(transit_days), 2)                         AS avg_transit_days
FROM fct_orders
GROUP BY customer_state
HAVING COUNT(*) >= 100
ORDER BY on_time_rate_pct;
SELECT * FROM kpi3_state_ontime LIMIT 5;

-- KPI4 late rate: cross-state vs same-state
CREATE OR REPLACE VIEW kpi4_cross_state AS
SELECT CASE WHEN is_cross_state THEN 'cross-state' ELSE 'same-state' END AS route_type,
       COUNT(*)                          AS n_orders,
       ROUND(100.0 * AVG(is_late::INT), 2) AS late_rate_pct,
       ROUND(AVG(transit_days), 2)       AS avg_transit_days,
       ROUND(AVG(total_lead_days), 2)    AS avg_total_lead_days
FROM fct_orders
GROUP BY route_type
ORDER BY route_type;
SELECT * FROM kpi4_cross_state;

-- KPI5 distribution of delay_days (negative = arrived before estimate)
CREATE OR REPLACE VIEW kpi5_delay_distribution AS
WITH b AS (
    SELECT CASE
             WHEN delay_days <= -15 THEN '1. 15+ days early'
             WHEN delay_days <= -8  THEN '2. 8-14 days early'
             WHEN delay_days <= -1  THEN '3. 1-7 days early'
             WHEN delay_days =  0   THEN '4. on estimated day'
             WHEN delay_days <=  3  THEN '5. 1-3 days late'
             WHEN delay_days <=  7  THEN '6. 4-7 days late'
             ELSE                        '7. 8+ days late'
           END AS delay_bucket
    FROM fct_orders
)
SELECT delay_bucket, COUNT(*) AS n_orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM b GROUP BY delay_bucket ORDER BY delay_bucket;
SELECT * FROM kpi5_delay_distribution;

-- Headline KPIs (dashboard tiles)
CREATE OR REPLACE VIEW kpi_headline AS
SELECT COUNT(*)                                            AS delivered_orders,
       ROUND(100.0 * AVG(CASE WHEN is_late THEN 0 ELSE 1 END), 2) AS on_time_rate_pct,
       ROUND(AVG(total_lead_days), 2)                      AS avg_lead_days
FROM fct_orders;
SELECT * FROM kpi_headline;
