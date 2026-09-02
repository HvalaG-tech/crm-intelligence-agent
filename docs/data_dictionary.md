# Data Dictionary — Olist CRM Dataset

## Source

[Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — Kaggle  
Period: October 2016 – August 2018 | ~100k orders | Brazil

---

## Canonical Tables (processed)

### `orders_enriched`

One row per **order item** (an order can have multiple items).

| Column | Type | Description |
|---|---|---|
| order_id | string | Unique order identifier |
| customer_id | string | Unique customer identifier (standardised from `customer_unique_id`) |
| purchase_date | datetime | Order purchase timestamp |
| order_status | string | delivered, shipped, canceled, etc. |
| order_value | float | Total payment value for the order |
| payment_type | string | credit_card, boleto, voucher, etc. |
| customer_city | string | Customer city |
| customer_state | string | 2-letter Brazilian state code (e.g. SP, RJ) |
| customer_zip_code_prefix | string | Zip code prefix |
| product_id | string | Product identifier |
| product_category_name | string | Product category (Portuguese) |
| seller_id | string | Seller identifier |
| seller_city | string | Seller city |
| seller_state | string | Seller state |

---

### `customers_enriched`

One row per **customer** with aggregated order history.

| Column | Type | Description |
|---|---|---|
| customer_id | string | Unique customer identifier |
| total_orders | int | Number of orders placed |
| total_revenue | float | Sum of all order values |
| avg_order_value | float | Average order value |
| first_purchase | datetime | Date of first order |
| last_purchase | datetime | Date of most recent order |
| customer_city | string | Customer city |
| customer_state | string | 2-letter state code |

---

### `geo`

Geolocation reference table.

| Column | Type | Description |
|---|---|---|
| zip_code | string | ZIP code prefix |
| lat | float | Latitude |
| lng | float | Longitude |
| city | string | City name |
| state | string | State code |

---

## Engineered Columns (added by analytics layer)

| Column | Source table | Description |
|---|---|---|
| recency_days | customers_enriched | Days since last purchase (from reference date) |
| tenure_days | customers_enriched | Days between first and last purchase |
| churned | customers_enriched | Binary label: 1 if recency_days ≥ inactivity_threshold |
| churn_score | customers_enriched | Churn probability [0–1] from RandomForest model |
| r_score, f_score, m_score | rfm output | RFM dimension scores |
| rfm_score | rfm output | Sum of r+f+m scores |
| segment | rfm output | Champions / Loyal Customers / At Risk / Lost |
| cluster | kmeans output | Integer cluster id |
| clv_estimated | clv output | Projected 12-month CLV in R$ |
