# Metric Definitions

Single source of truth for delivery KPIs. Used by `sql/03_kpi_analysis.sql` and given to agent **v1** as context.

## Table: fct_orders
Grain: **one row per delivered order** that passed data-quality checks (96,217 rows).
Orders that were not delivered (shipped, canceled, ...) are NOT in this table.

| Column | Definition |
|---|---|
| order_id | Unique order key |
| customer_id | Customer key (one per order in this dataset) |
| purchase_month | First day of the month the order was **purchased** (DATE). "Month" in questions means this column. |
| purchase_ts / carrier_ts / delivered_ts | Purchase, handed-to-carrier and delivered-to-customer timestamps |
| estimated_date | Delivery date promised to the customer (DATE) |
| customer_state / seller_state | 2-letter Brazilian state code. seller_state = seller of the first item in the order. "State" with no qualifier means **customer_state**. |
| n_sellers | Number of distinct sellers in the order |
| is_cross_state | TRUE when customer_state <> seller_state |
| handling_days | Days from purchase to handed-to-carrier (fractional). Also called "processing" or "before shipping". |
| transit_days | Days from carrier to customer (fractional). Also called "shipping" or "in transit". |
| total_lead_days | Days from purchase to delivery = handling_days + transit_days. "Lead time" / "delivery time" means this. |
| delay_days | Delivered date minus estimated date, in whole days. Negative = early, 0 = on the estimated day, positive = late. |
| is_late | TRUE when delay_days > 0. Delivering on the estimated day counts as on time. |

## Metrics
- **On-time rate (%)** = 100 × share of orders with `is_late = FALSE`. Report as a percentage rounded to 2 decimals.
  `ROUND(100.0 * AVG(CASE WHEN is_late THEN 0 ELSE 1 END), 2)`
- **Late rate (%)** = 100 × share of orders with `is_late = TRUE`, rounded to 2 decimals. Late rate = 100 − on-time rate.
- **Average lead time** = `AVG(total_lead_days)` (mean, not median), rounded to 2 decimals.
- **Average delay of late orders** = `AVG(delay_days)` over rows where `is_late` only.
- **Number of orders** = `COUNT(*)` of fct_orders rows.

## Rules
- Monthly trends cover **2017-01 to 2018-08** only (other months have very few orders).
- Rankings of states (best/worst) include only states with **at least 100 orders**.
- Round days and percentages to 2 decimals.
- Use DuckDB SQL. Only query `fct_orders`.
