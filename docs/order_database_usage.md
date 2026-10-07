# Traceable order database

The original 70 mock orders remain historical fixtures. A separate 70-order
Zenodo demo uses expert garment-type annotations, source IDs and front photos.
Prices, transaction dates, delivery states and retailer assignments are synthetic.
The photographs do not establish actual purchases from the assigned retailer.
Annotations describe the catalogue side only; they must never be fed to the
image classifier as its prediction. These samples are not the YOLO held-out set.

Build from the locally downloaded Zenodo 8386668 archive:

```sh
python -m scripts.build_traceable_orders --source /path/to/extracted
```

Output: `artifacts/traceable_orders/orders.json`, `orders.db`, copied images,
and `date_results.json`. Reimport is idempotent; conflicting stored orders fail.
The supplied dates produce 70 PASS results by construction. This verifies lookup
and comparison, not transaction authenticity or image-model accuracy.

Query a date mismatch:

```sh
python -m scripts.check_order_dates --database artifacts/traceable_orders/orders.db --order-id ZEN001 --purchase-date 2026-09-02 --request-date 2026-09-15
```

Use SQLite for the existing pipeline and order list:

```sh
REFUND_ORDER_DB=artifacts/traceable_orders/orders.db python -m app.server
```

The date-check command has a configurable research window (30 days by default).
It is separate from retailer policy retrieval and does not establish legal rights.
Images for individual applications belong in the `refund_cases` table; the
database API enforces an existing order through a foreign key. The current UI
still uses its existing application store; migrating that store is outstanding.

Eight database tests cover correct dates, mismatches, invalid dates, requests
before delivery, requests outside the window, unknown orders, conflicting
imports, and case/order linkage. Current model assessment remains pending until
the CLIP weights are available. Product confidence thresholds remain provisional;
do not report zero-shot scores as calibrated match probabilities.
