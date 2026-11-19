# Concise semantic dictionary

The owner supplied the actual generated dictionary for the reviewed local snapshot. See [the complete observed inventory](observed_source_dictionary.md) for exact headers, records, blanks and distinct counts. This document explains field meanings and remaining semantic assumptions. The cloud environment has not independently inspected the underlying CSVs. Structural observations do not by themselves establish business semantics or availability at prediction time.

| Expected field(s) | Proposed interpretation | Raw handling / unresolved assumption |
|---|---|---|
| `order_id` | Order identifier | Text; do not infer order count from child rows |
| `customer_id` | Customer record referenced by an order | Text; test parent uniqueness and coverage |
| `customer_unique_id` | Repeat-person linkage | Text; never use as a substitute for the order's customer foreign key |
| `order_item_id` | Item sequence within an order | Text; only composite uniqueness is expected |
| `payment_sequential` | Payment sequence within an order | Text; only composite uniqueness is expected |
| `review_id` | Source review identifier | Observed nonunique; retain technical source-record identity |
| `product_id`, `seller_id` | Item references | Text; orphan checks |
| `order_status` | Historical exported order status | Discover actual values before defining a domain contract |
| `order_purchase_timestamp` | Purchase event time | Parse naive timestamp; no timezone conversion |
| `order_approved_at` | Approval time | Missingness and ordering require review |
| `order_delivered_carrier_date` | Carrier handoff time | Missingness and ordering require review |
| `order_delivered_customer_date` | Customer delivery time | Missing may reflect order status; never impute delivery |
| `order_estimated_delivery_date` | Estimated delivery promise | Promise semantics and date granularity remain unverified |
| `shipping_limit_date` | Item shipping deadline | Parse separately from actual shipping events |
| `price` | Item value | Exact Decimal/numeric sum, never binary floating point |
| `freight_value` | Item freight amount | Keep separate from item price |
| `payment_value` | Payment-record amount | Aggregate per order before joining |
| `review_score` | Customer rating | Accepted scale must be verified on actual source |
| `review_comment_title`, `review_comment_message` | Original customer text | Preserve Portuguese, accents, blanks, quotes and newlines |
| `review_creation_date`, `review_answer_timestamp` | Source review timestamps | Parse without assuming a review business key |
| `product_category_name` | Source product category | 610 missing values; 13 nonblank product rows lack a supplied translation; see DQ-001 |
| `product_category_name_english` | Supplied category translation | No invented translation |
| ZIP-prefix fields | Location prefix | Text preserves leading zeros; not a unique geographic record key |
| Other product/location fields | Discovered source attributes | Preserve unchanged; meanings and units require source review |

Empty and whitespace-only values are counted separately. Distinct counts include empty strings. Missing-rate denominators are table row counts; an empty table has an undefined (`null`) rate. Source columns are not coerced based on their names. Configured date/money columns were included in the owner’s local validation; no exact monetary sums or timestamp ranges were shared. Five distinct review-score values do not prove their allowed domain. Source misspellings `product_name_lenght` and `product_description_lenght` are retained unchanged.
