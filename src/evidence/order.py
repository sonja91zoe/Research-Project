"""Local JSON order retrieval for the Member 3 Week 5 prototype."""

import json
import os
from pathlib import Path

from src.evidence.models import OrderRecord


DEFAULT_ORDER_DB = Path("data/orders/orders.json")


def load_orders(filename: str | Path = DEFAULT_ORDER_DB) -> dict[str, OrderRecord]:
    """Load order records indexed by normalized order ID."""

    database = os.getenv('REFUND_ORDER_DB')
    if database and Path(filename) == DEFAULT_ORDER_DB:
        filename = database
    path = Path(filename)
    if path.suffix.lower() in {'.db', '.sqlite', '.sqlite3'}:
        from src.evidence.database import connect
        with connect(path) as db:
            records = [json.loads(row['record_json']) for row in
                       db.execute('SELECT record_json FROM orders ORDER BY order_id')]
        return {r['order_id'].upper(): OrderRecord(**r) for r in records}
    with path.open(encoding="utf-8") as order_file:
        records = json.load(order_file)

    orders = {record["order_id"].upper(): OrderRecord(**record) for record in records}
    if len(orders) != len(records):
        raise ValueError("order database contains duplicate order IDs")
    return orders


def retrieve_order(
    order_id: str,
    filename: str | Path = DEFAULT_ORDER_DB,
) -> OrderRecord | None:
    """Return an order by ID, or None when the order does not exist."""

    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("order_id must be a non-empty string")
    return load_orders(filename).get(order_id.strip().upper())
