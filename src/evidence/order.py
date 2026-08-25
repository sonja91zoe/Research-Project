"""Local JSON order retrieval for the Member 3 Week 5 prototype."""

import json
from pathlib import Path

from src.evidence.models import OrderRecord


DEFAULT_ORDER_DB = Path("data/orders/orders.json")


def load_orders(filename: str | Path = DEFAULT_ORDER_DB) -> dict[str, OrderRecord]:
    """Load order records indexed by normalized order ID."""

    with Path(filename).open(encoding="utf-8") as order_file:
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
