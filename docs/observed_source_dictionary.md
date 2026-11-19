# Observed source dictionary — local Olist snapshot

**Provenance:** Transcribed from the generated `reports/inspection.dictionary.md` supplied by the project owner in this conversation, alongside the successful ingestion into `raw_dbfbd3a2636389441845` and its validation output. The cloud environment has not independently inspected these source CSVs or the owner’s PostgreSQL database. Full file checksums and run timestamps remain in the local inspection manifest; the schema suffix is not the full snapshot ID.

All source fields are stored as text in raw PostgreSQL tables. Missing means empty or whitespace-only, counted separately below. Distinct counts include empty strings. No row-level customer data, passwords, connection strings, local filesystem paths, or source CSVs are included.

## customers

Source: `olist_customers_dataset.csv`; records: 99441

| Column | Empty | Whitespace-only | Distinct including empty |
|---|---:|---:|---:|
| customer_id | 0 | 0 | 99441 |
| customer_unique_id | 0 | 0 | 96096 |
| customer_zip_code_prefix | 0 | 0 | 14994 |
| customer_city | 0 | 0 | 4119 |
| customer_state | 0 | 0 | 27 |

## geolocation

Source: `olist_geolocation_dataset.csv`; records: 1000163

| Column | Empty | Whitespace-only | Distinct including empty |
|---|---:|---:|---:|
| geolocation_zip_code_prefix | 0 | 0 | 19015 |
| geolocation_lat | 0 | 0 | 717372 |
| geolocation_lng | 0 | 0 | 717615 |
| geolocation_city | 0 | 0 | 8011 |
| geolocation_state | 0 | 0 | 27 |

## items

Source: `olist_order_items_dataset.csv`; records: 112650

| Column | Empty | Whitespace-only | Distinct including empty |
|---|---:|---:|---:|
| order_id | 0 | 0 | 98666 |
| order_item_id | 0 | 0 | 21 |
| product_id | 0 | 0 | 32951 |
| seller_id | 0 | 0 | 3095 |
| shipping_limit_date | 0 | 0 | 93318 |
| price | 0 | 0 | 5968 |
| freight_value | 0 | 0 | 6999 |

## payments

Source: `olist_order_payments_dataset.csv`; records: 103886

| Column | Empty | Whitespace-only | Distinct including empty |
|---|---:|---:|---:|
| order_id | 0 | 0 | 99440 |
| payment_sequential | 0 | 0 | 29 |
| payment_type | 0 | 0 | 5 |
| payment_installments | 0 | 0 | 24 |
| payment_value | 0 | 0 | 29077 |

## reviews

Source: `olist_order_reviews_dataset.csv`; records: 99224

| Column | Empty | Whitespace-only | Distinct including empty |
|---|---:|---:|---:|
| review_id | 0 | 0 | 98410 |
| order_id | 0 | 0 | 98673 |
| review_score | 0 | 0 | 5 |
| review_comment_title | 87656 | 2 | 4528 |
| review_comment_message | 58247 | 27 | 36160 |
| review_creation_date | 0 | 0 | 636 |
| review_answer_timestamp | 0 | 0 | 98248 |

## orders

Source: `olist_orders_dataset.csv`; records: 99441

| Column | Empty | Whitespace-only | Distinct including empty |
|---|---:|---:|---:|
| order_id | 0 | 0 | 99441 |
| customer_id | 0 | 0 | 99441 |
| order_status | 0 | 0 | 8 |
| order_purchase_timestamp | 0 | 0 | 98875 |
| order_approved_at | 160 | 0 | 90734 |
| order_delivered_carrier_date | 1783 | 0 | 81019 |
| order_delivered_customer_date | 2965 | 0 | 95665 |
| order_estimated_delivery_date | 0 | 0 | 459 |

## products

Source: `olist_products_dataset.csv`; records: 32951

| Column | Empty | Whitespace-only | Distinct including empty |
|---|---:|---:|---:|
| product_id | 0 | 0 | 32951 |
| product_category_name | 610 | 0 | 74 |
| product_name_lenght | 610 | 0 | 67 |
| product_description_lenght | 610 | 0 | 2961 |
| product_photos_qty | 610 | 0 | 20 |
| product_weight_g | 2 | 0 | 2205 |
| product_length_cm | 2 | 0 | 100 |
| product_height_cm | 2 | 0 | 103 |
| product_width_cm | 2 | 0 | 96 |

## sellers

Source: `olist_sellers_dataset.csv`; records: 3095

| Column | Empty | Whitespace-only | Distinct including empty |
|---|---:|---:|---:|
| seller_id | 0 | 0 | 3095 |
| seller_zip_code_prefix | 0 | 0 | 2246 |
| seller_city | 0 | 0 | 611 |
| seller_state | 0 | 0 | 23 |

## category_translation

Source: `product_category_name_translation.csv`; records: 71

| Column | Empty | Whitespace-only | Distinct including empty |
|---|---:|---:|---:|
| product_category_name | 0 | 0 | 71 |
| product_category_name_english | 0 | 0 | 71 |

## Interpretation limits

Distinct counts are not full key proofs for composite keys. Five distinct review scores do not establish their exact allowed values. Equal missing counts across product fields do not prove the same rows are missing. Date ranges, exact monetary totals, status values, duplicate-key details and the review composite-key profile were not supplied in this dictionary; none are invented here.

Review ID and order ID are individually nonunique in reviews. ZIP prefix is nonunique in geolocation. Product category has 74 distinct raw values including the empty string; do not report 74 populated categories. See [the known exception](data_quality_exceptions.md) for translation coverage.
