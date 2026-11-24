# Data model and grain

**Reviewed against the owner-supplied local dictionary and validation output.** All configured relationships passed except [DQ-001](data_quality_exceptions.md). Evidence applies to schema `raw_dbfbd3a2636389441845`; the same source inventory and reconciliation result were subsequently reproduced from the official archive in this environment. Business-key checks remain assertions in code, not raw database constraints.

The milestone implements source-shaped raw tables and ingestion metadata. Typed `core` tables and business analytics are deferred until observed defects and schema are reviewed. This avoids encoding unverified primary keys or dropping irregular rows.

| Logical table | Grain/key expectation tested by the pipeline | Relationship or caution |
|---|---|---|
| orders | order; candidate key `order_id` | Each order references a customer record |
| items | item within order; `(order_id, order_item_id)` | Many items per order; each references product and seller |
| payments | payment sequence within order; `(order_id, payment_sequential)` | Many payments per order |
| reviews | retained source record; no assumed business key | 99,224 rows; 98,410 review IDs; 98,673 order IDs; neither individual field is unique; composite result not supplied |
| customers | customer record; candidate key `customer_id` | `customer_unique_id` is a person-level identifier, not assumed unique per source row |
| sellers | seller; candidate key `seller_id` | Many items can reference one seller |
| products | product; candidate key `product_id` | Many items can reference one product |
| geolocation | source location record; no assumed business key | 1,000,163 rows across 19,015 ZIP prefixes; never join directly at ZIP-prefix grain |
| category_translation | source category; candidate key `product_category_name` | Missing mappings are surfaced rather than dropped |

Physical layout:

- `ingestion.snapshots`: full snapshot ID, schema name, database load timestamp and complete inspection manifest (JSONB).
- `raw_<snapshot-hash-prefix>.<logical-table>`: discovered source columns stored as text plus `__source_row bigint PRIMARY KEY`.
- Source blank fields remain `''`. SQL NULL is not substituted. `__source_row` is lineage, not a business key.
- Snapshot schema names use 20 hexadecimal characters; a collision with a different full ID is rejected.

Raw tables deliberately lack business foreign keys and business-key constraints: raw ingestion must preserve violations so they can be investigated. Provisional uniqueness and relationships are checked separately. No review record is arbitrarily selected as canonical.

## The order join trap

Orders → items, orders → payments, and orders → reviews are separate one-to-many relationships. Joining their unaggregated child records can multiply both counts and money. A synthetic illustration: one order with 2 items, 2 payments, and 2 reviews yields 8 joined rows. This is a teaching example, not an Olist finding.

The integration fixture intentionally exercises that shape. The validation query first groups each child table by `order_id`, then LEFT JOINs those single-order summaries to orders. It verifies:

1. Joined row count equals the source order-record count.
2. Summed item price is unchanged.
3. Summed item freight is unchanged.
4. Summed payment value is unchanged.

Order-key uniqueness and relationship checks must pass as well: a conserved row count alone does not establish valid grain. LEFT JOIN retains orders without children. Orphans are detected independently rather than hidden by an inner join. Reviews enter this check only as counts, without assuming their uniqueness.

**Item value + freight is not asserted equal to payments.** Such equality requires inspecting actual business semantics and exceptions. Each monetary measure is reconciled independently from source to database and through the safe join.

Geolocation is not joined directly by ZIP prefix in this milestone. A later location dimension needs an explicit, reviewed aggregation rule. Seller/category reporting also needs an attribution rule for multi-seller or multi-category orders.

## Snapshot observations

Orders and customer records each have 99,441 rows and unique `customer_id` values in this release. With their passed reference check, that is an observed one-to-one mapping between exported order and customer records. It does not make `customer_unique_id` unique: 96,096 such identifiers appear in customers, and person-level repeat-order analysis must distinguish those grains.

Items have 112,650 rows across 98,666 orders; payments have 103,886 rows across 99,440 orders. These support one-to-many child tables and the need to retain orders without a child. Counts and distinct values come from the owner-supplied dictionary, not hard-coded data-test thresholds.

Category enrichment must retain all products with LEFT JOIN. The 610 missing categories and 13 present-but-unmapped categories need different labels in a later typed/reporting layer; no source repair is made here.
