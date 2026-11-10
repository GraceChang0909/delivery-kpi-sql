-- 00_load_raw.sql
-- Load the Olist CSVs into raw tables. (run_sql.py sets file_search_path to data/raw/)

CREATE OR REPLACE TABLE raw_orders      AS SELECT * FROM read_csv_auto('olist_orders_dataset.csv');
CREATE OR REPLACE TABLE raw_order_items AS SELECT * FROM read_csv_auto('olist_order_items_dataset.csv');
CREATE OR REPLACE TABLE raw_customers   AS SELECT * FROM read_csv_auto('olist_customers_dataset.csv');
CREATE OR REPLACE TABLE raw_sellers     AS SELECT * FROM read_csv_auto('olist_sellers_dataset.csv');

-- Row counts
SELECT 'raw_orders' AS tbl, COUNT(*) AS n FROM raw_orders
UNION ALL SELECT 'raw_order_items', COUNT(*) FROM raw_order_items
UNION ALL SELECT 'raw_customers',   COUNT(*) FROM raw_customers
UNION ALL SELECT 'raw_sellers',     COUNT(*) FROM raw_sellers;
