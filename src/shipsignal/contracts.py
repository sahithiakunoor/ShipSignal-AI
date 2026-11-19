"""Provisional expectations, NOT observations of a locally inspected Olist release.

Contracts are validated against discovered headers. Reviews and geolocation deliberately
have no assumed business primary key. No data is deduplicated or repaired.
"""

FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}
KEYS = {
    "orders": ["order_id"],
    "items": ["order_id", "order_item_id"],
    "payments": ["order_id", "payment_sequential"],
    "customers": ["customer_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
    "category_translation": ["product_category_name"],
}
CANDIDATES = {
    "reviews": [["review_id"], ["order_id"], ["review_id", "order_id"]],
    "geolocation": [["geolocation_zip_code_prefix"]],
}
# child table, child column, parent table, parent column, missing child allowed
RELATIONSHIPS = [
    ("orders", "customer_id", "customers", "customer_id", False),
    ("items", "order_id", "orders", "order_id", False),
    ("items", "product_id", "products", "product_id", False),
    ("items", "seller_id", "sellers", "seller_id", False),
    ("payments", "order_id", "orders", "order_id", False),
    ("reviews", "order_id", "orders", "order_id", False),
    ("products", "product_category_name", "category_translation", "product_category_name", True),
]
MONEY = {"items": ["price", "freight_value"], "payments": ["payment_value"]}
# Candidate date fields; only inspected when present. Absence is reported by profile.
DATES = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}
