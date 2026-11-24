"""Approved, order-grain SQL and a reproducible derived analytics table."""

from datetime import date

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .database import schema_name, validate_database
from .settings import NotReady
from .validation import quality_checks

# No raw child table is joined before aggregation. Source tables remain unchanged.
FACT_SQL = """
WITH i AS (
 SELECT order_id, count(*)::int item_count, count(DISTINCT seller_id)::int seller_count,
        sum(price::numeric) item_value, sum(freight_value::numeric) freight_value
 FROM {items} GROUP BY order_id
), p AS (
 SELECT order_id, count(*)::int payment_count, sum(payment_value::numeric) payment_value
 FROM {payments} GROUP BY order_id
), o AS (
 SELECT o.order_id, o.customer_id, o.order_status,
   nullif(btrim(o.order_purchase_timestamp),'')::timestamp purchased_at,
   nullif(btrim(o.order_approved_at),'')::timestamp approved_at,
   nullif(btrim(o.order_delivered_customer_date),'')::timestamp delivered_at,
   nullif(btrim(o.order_estimated_delivery_date),'')::timestamp estimated_at,
   c.customer_state, c.customer_city,
   coalesce(i.item_count,0) item_count, coalesce(i.seller_count,0) seller_count,
   coalesce(i.item_value,0) item_value, coalesce(i.freight_value,0) freight_value,
   coalesce(p.payment_count,0) payment_count, coalesce(p.payment_value,0) payment_value
 FROM {orders} o JOIN {customers} c USING(customer_id)
 LEFT JOIN i USING(order_id) LEFT JOIN p USING(order_id)
), marked AS (
 SELECT *, (order_status='delivered' AND delivered_at IS NOT NULL
   AND estimated_at IS NOT NULL AND delivered_at>=purchased_at
   AND estimated_at>=purchased_at) eligible_delivery
 FROM o
)
SELECT *, CASE WHEN eligible_delivery THEN delivered_at>estimated_at END is_late,
 CASE WHEN eligible_delivery THEN extract(epoch FROM delivered_at-purchased_at)/86400 END delivery_days,
 CASE WHEN eligible_delivery AND delivered_at>estimated_at
   THEN extract(epoch FROM delivered_at-estimated_at)/86400 END late_days
FROM marked
"""

METRIC_SELECT = """
 count(*)::int orders,
 count(*) FILTER(WHERE eligible_delivery)::int eligible_delivered_orders,
 count(*) FILTER(WHERE NOT eligible_delivery)::int excluded_orders,
 count(*) FILTER(WHERE is_late)::int late_orders,
 avg(is_late::int) FILTER(WHERE eligible_delivery)::float late_delivery_rate,
 avg(delivery_days)::float average_delivery_days,
 percentile_cont(0.5) WITHIN GROUP(ORDER BY delivery_days)::float median_delivery_days,
 avg(late_days)::float average_late_days,
 min(purchased_at)::date first_purchase, max(purchased_at)::date last_purchase
"""


def connect(dsn):
    if not dsn:
        raise NotReady("Configure DATABASE_URL privately before using the application.")
    return psycopg.connect(
        dsn, row_factory=dict_row, connect_timeout=5, options="-c statement_timeout=30000"
    )


def build(dsn, manifest):
    failures = [c for c in quality_checks(manifest) if not c["passed"]]
    # Explicit reviewed snapshot exception, not a blanket relationship waiver.
    allowed = all(
        c["check"] == "products.product_category_name.relationship"
        and c["detail"].get("orphan_rows") == 13
        and c["detail"].get("missing_child_rows") == 610
        and c["detail"].get("parent_missing_rows") == 0
        and c["detail"].get("parent_duplicate_excess_rows") == 0
        for c in failures
    )
    if failures and not allowed:
        raise ValueError("Source quality has unreviewed failures; run shipsignal validate.")
    checks = validate_database(dsn, manifest)
    if not all(c["passed"] for c in checks):
        raise ValueError("Database reconciliation failed; analytics build refused.")
    schema = schema_name(manifest)
    with connect(dsn) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('shipsignal_analytics'))")
        if failures:
            unmatched = conn.execute(
                sql.SQL("""SELECT p.product_category_name category,count(*)::int products
                FROM {products} p LEFT JOIN {translation} t USING(product_category_name)
                WHERE btrim(p.product_category_name)<>'' AND t.product_category_name IS NULL
                GROUP BY p.product_category_name""").format(
                    products=sql.Identifier(schema, "products"),
                    translation=sql.Identifier(schema, "category_translation"),
                )
            ).fetchall()
            if {row["category"]: row["products"] for row in unmatched} != {
                "pc_gamer": 3,
                "portateis_cozinha_e_preparadores_de_alimentos": 10,
            }:
                raise ValueError("Translation exception categories differ from reviewed DQ-001.")
        conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")
        conn.execute("DROP TABLE IF EXISTS analytics.order_fact")
        query = sql.SQL("CREATE TABLE analytics.order_fact AS " + FACT_SQL).format(
            **{t: sql.Identifier(schema, t) for t in ("orders", "items", "payments", "customers")}
        )
        conn.execute(query)
        conn.execute("ALTER TABLE analytics.order_fact ADD PRIMARY KEY(order_id)")
        conn.execute("CREATE INDEX ON analytics.order_fact(purchased_at)")
        conn.execute("CREATE INDEX ON analytics.order_fact(customer_state)")
        count = conn.execute("SELECT count(*) n FROM analytics.order_fact").fetchone()["n"]
        if count != manifest["tables"]["orders"]["rows"]:
            raise ValueError("Derived table did not conserve order count")
        conn.execute("""CREATE TABLE IF NOT EXISTS analytics.dataset (
          singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
          snapshot_id text NOT NULL, raw_schema text NOT NULL, metadata jsonb NOT NULL)""")
        metadata = {
            "historical": True,
            "source_url": manifest["source_url"],
            "source_tables": {t: v["rows"] for t, v in manifest["tables"].items()},
            "quality_findings": failures,
            "database_checks_passed": len(checks),
        }
        conn.execute(
            """INSERT INTO analytics.dataset VALUES(true,%s,%s,%s)
          ON CONFLICT(singleton) DO UPDATE SET snapshot_id=excluded.snapshot_id,
          raw_schema=excluded.raw_schema, metadata=excluded.metadata""",
            (manifest["snapshot_id"], schema, Jsonb(metadata)),
        )
        conn.execute("ANALYZE analytics.order_fact")
    return {
        "snapshot_id": manifest["snapshot_id"],
        "orders": count,
        "quality_exception_count": len(failures),
    }


def dataset(conn):
    if not conn.execute("SELECT to_regclass('analytics.dataset') present").fetchone()["present"]:
        raise NotReady("Run python -m shipsignal.tasks analytics after real-data ingestion.")
    row = conn.execute("SELECT * FROM analytics.dataset WHERE singleton").fetchone()
    if not row:
        raise NotReady("No active historical dataset has been built.")
    return row


def where(start: date | None = None, end: date | None = None, state: str | None = None):
    conditions, params = [], []
    if start:
        conditions.append("purchased_at >= %s::date")
        params.append(start)
    if end:
        conditions.append("purchased_at < %s::date + interval '1 day'")
        params.append(end)
    if state:
        conditions.append("customer_state=%s")
        params.append(state)
    return " WHERE " + " AND ".join(conditions) if conditions else "", params


def overview(dsn, start=None, end=None, state=None):
    clause, params = where(start, end, state)
    with connect(dsn) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        active = dataset(conn)
        kpis = conn.execute(
            "SELECT " + METRIC_SELECT + " FROM analytics.order_fact" + clause, params
        ).fetchone()
        months = conn.execute(
            "SELECT to_char(purchased_at,'YYYY-MM') AS month,"
            + METRIC_SELECT
            + " FROM analytics.order_fact"
            + clause
            + " GROUP BY 1 ORDER BY 1",
            params,
        ).fetchall()
        regions = conn.execute(
            "SELECT customer_state state,"
            + METRIC_SELECT
            + " FROM analytics.order_fact"
            + clause
            + " GROUP BY 1 ORDER BY orders DESC",
            params,
        ).fetchall()
        statuses = conn.execute(
            "SELECT order_status status,count(*)::int orders FROM analytics.order_fact"
            + clause
            + " GROUP BY 1 ORDER BY 2 DESC",
            params,
        ).fetchall()
        states = conn.execute(
            "SELECT DISTINCT customer_state state FROM analytics.order_fact ORDER BY 1"
        ).fetchall()
        coverage = conn.execute(
            "SELECT min(purchased_at)::date start,max(purchased_at)::date end FROM analytics.order_fact"
        ).fetchone()
    return {
        "snapshot_id": active["snapshot_id"],
        "metadata": active["metadata"],
        "filters": {"start": start, "end": end, "state": state},
        "coverage": coverage,
        "kpis": kpis,
        "monthly": months,
        "regions": regions,
        "statuses": statuses,
        "states": [r["state"] for r in states],
        "query_id": "delivery_overview_v1",
        "definition": "Purchase-date cohorts. Late means actual timestamp exceeds estimated timestamp. "
        "Rate denominator: delivered orders with present, nonnegative purchase-relative actual and estimated timestamps. "
        "Canceled, unavailable and unobserved outcomes remain in order volume but are excluded from delivery statistics.",
    }
