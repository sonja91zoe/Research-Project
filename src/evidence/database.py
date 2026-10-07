"""SQLite order storage and auditable date checks for research cases."""
import json
import sqlite3
from datetime import date
from pathlib import Path


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def initialize(path, records):
    """Import new orders without silently replacing existing records."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            purchase_date TEXT NOT NULL,
            delivery_date TEXT,
            record_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS refund_cases (
            case_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL REFERENCES orders(order_id),
            claim_text TEXT NOT NULL,
            image_path TEXT NOT NULL,
            request_date TEXT NOT NULL
        );
        ''')
        for record in records:
            purchase = date.fromisoformat(record['purchase_date'])
            delivery = record.get('delivery_date')
            if delivery and date.fromisoformat(delivery) < purchase:
                raise ValueError('Delivery precedes purchase')
            key = record['order_id'].strip().upper()
            encoded = json.dumps(record, sort_keys=True)
            old = db.execute('SELECT record_json FROM orders WHERE order_id=?', (key,)).fetchone()
            if old:
                if old['record_json'] != encoded:
                    raise ValueError(f'Conflicting existing order: {key}')
                continue
            db.execute('INSERT INTO orders VALUES (?,?,?,?)',
                       (key, purchase.isoformat(), delivery, encoded))


def lookup(path, order_id):
    with connect(path) as db:
        row = db.execute('SELECT record_json FROM orders WHERE order_id=?',
                         (order_id.strip().upper(),)).fetchone()
    return json.loads(row['record_json']) if row else None


def verify_dates(path, order_id, submitted_purchase_date, request_date, window_days=30):
    """Compare supplied dates with stored records; no transaction authenticity claim."""
    order = lookup(path, order_id)
    result = {'order_id': order_id, 'order_found': order is not None,
              'purchase_date_match': None, 'request_after_delivery': None,
              'within_return_window': None, 'status': 'ORDER_NOT_FOUND'}
    if order is None:
        return result
    try:
        submitted = date.fromisoformat(submitted_purchase_date)
        requested = date.fromisoformat(request_date)
    except (ValueError, TypeError):
        return {**result, 'status': 'INVALID_DATE'}
    result['purchase_date_match'] = submitted == date.fromisoformat(order['purchase_date'])
    if not order.get('delivery_date'):
        return {**result, 'status': 'DELIVERY_DATE_MISSING'}
    days = (requested - date.fromisoformat(order['delivery_date'])).days
    result.update(request_after_delivery=days >= 0, within_return_window=0 <= days <= window_days)
    result['status'] = ('DATE_MISMATCH' if not result['purchase_date_match'] else
                        'BEFORE_DELIVERY' if days < 0 else
                        'OUTSIDE_WINDOW' if days > window_days else 'PASS')
    return result


def save_case(path, case_id, order_id, claim_text, image_path, request_date):
    date.fromisoformat(request_date)
    with connect(path) as db:
        db.execute('INSERT INTO refund_cases VALUES (?,?,?,?,?)',
                   (case_id, order_id.strip().upper(), claim_text, image_path, request_date))
