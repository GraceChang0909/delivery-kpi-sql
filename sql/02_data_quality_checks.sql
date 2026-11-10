-- 02_data_quality_checks.sql
-- Each check returns the number of offending rows.
-- Rows failing DQ2–DQ4 are tagged in stg_delivered_orders.dq_issue and excluded from fct_orders.

-- DQ summary
SELECT 'DQ1 duplicate order_id in fct_orders' AS check_name,
       COUNT(*) - COUNT(DISTINCT order_id)    AS n_rows,
       'should be 0 (join fan-out check)'     AS handling
FROM fct_orders
UNION ALL
SELECT 'DQ2 timestamps out of order', COUNT(*), 'excluded from fct_orders'
FROM stg_delivered_orders WHERE dq_issue IN ('delivered_before_shipped', 'shipped_before_purchase')
UNION ALL
SELECT 'DQ3 delivered but missing delivery/carrier date', COUNT(*), 'excluded from fct_orders'
FROM stg_delivered_orders WHERE dq_issue = 'missing_timestamp'
UNION ALL
SELECT 'DQ4 lead time < 0 or > 100 days', COUNT(*), 'excluded from fct_orders'
FROM stg_delivered_orders WHERE dq_issue = 'lead_time_outlier';

-- Exclusions by dq_issue
SELECT dq_issue, COUNT(*) AS n_rows
FROM stg_delivered_orders
WHERE dq_issue IS NOT NULL
GROUP BY dq_issue
ORDER BY n_rows DESC;

-- Rows kept vs excluded
SELECT COUNT(*)                                  AS delivered_orders,
       COUNT(*) FILTER (WHERE dq_issue IS NULL)  AS kept_in_fct_orders,
       COUNT(*) FILTER (WHERE dq_issue IS NOT NULL) AS excluded,
       ROUND(100.0 * COUNT(*) FILTER (WHERE dq_issue IS NOT NULL) / COUNT(*), 2) AS excluded_pct
FROM stg_delivered_orders;
