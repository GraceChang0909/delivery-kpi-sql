| Version | Simple (5) | KPI (5) | Comparison (5) | Overall (15) |
|---|---|---|---|---|
| v0 | 5/5 | 5/5 | 3/5 | 13/15 (87%) |
| v1 | 5/5 | 5/5 | 5/5 | 15/15 (100%) |

## Failures

### c03 v0: Which month had the lowest on-time rate?
- predicted: `[{'purchase_month': Timestamp('2016-09-01 00:00:00'), 'on_time_rate': 0.0}]`
- gold: `[{'purchase_month': Timestamp('2018-03-01 00:00:00'), 'on_time_rate_pct': 81.05}]`
```sql
SELECT
    purchase_month,
    AVG(CASE WHEN is_late THEN 0.0 ELSE 1.0 END) AS on_time_rate
FROM fct_orders
WHERE delivered_ts IS NOT NULL
  AND is_late IS NOT NULL
GROUP BY purchase_month
ORDER BY on_time_rate ASC, purchase_month ASC
LIMIT 1
```

### c04 v0: Which 3 seller states have the longest average transit time?
- predicted: `[{'seller_state': 'AM', 'avg_transit_days': 44.41}, {'seller_state': 'RO', 'avg_transit_days': 15.810000000000002}, {'seller_state': 'CE', 'avg_transit_days': 13.078690476190477}]`
- gold: `[{'seller_state': 'MA', 'avg_transit_days': 12.93}, {'seller_state': 'MT', 'avg_transit_days': 11.44}, {'seller_state': 'PE', 'avg_transit_days': 10.61}]`
```sql
SELECT
    seller_state,
    AVG(transit_days) AS avg_transit_days
FROM fct_orders
WHERE transit_days IS NOT NULL
GROUP BY seller_state
ORDER BY avg_transit_days DESC
LIMIT 3
```
