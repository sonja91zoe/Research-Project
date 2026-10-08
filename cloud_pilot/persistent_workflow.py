"""Opt-in, single-user local SQLite workflow. Not a public multi-user store."""
import json
import hashlib
from dataclasses import asdict
from pathlib import Path
from app.refund_service import now
from cloud_pilot.workflow import SessionRefundService
from src.evidence.database import connect, initialize
from src.evidence.order import load_orders, DEFAULT_ORDER_DB


class LocalSqliteRefundService(SessionRefundService):
    def __init__(self, runtime, database, **kwargs):
        super().__init__(runtime, **kwargs)
        self.database = Path(database)
        initialize(self.database, [asdict(o) for o in load_orders(self.order_source or DEFAULT_ORDER_DB).values()])
        # Keep historical orders available after changing the new-case catalog.
        # initialize adds records without replacing existing order identities.
        self.order_source = self.database
        with connect(self.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS workflow_records (case_id TEXT PRIMARY KEY REFERENCES refund_cases(case_id), updated_at TEXT NOT NULL, record_json TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS evidence_images (sha256 TEXT PRIMARY KEY, content BLOB NOT NULL)')

    def _save_assessment(self, record, data):
        record['assessments'][-1]['image_sha256'] = hashlib.sha256(data).hexdigest()
        return self._save(record, image_data=data)

    def image(self, case_id, revision):
        record = self.get(case_id)
        if revision < 0 or revision >= len(record['assessments']):
            raise ValueError('Invalid evidence revision.')
        digest = record['assessments'][revision].get('image_sha256')
        with connect(self.database) as db:
            row = db.execute('SELECT content FROM evidence_images WHERE sha256=?', (digest,)).fetchone()
        if row is None:
            raise ValueError('This historical assessment has no retained image.')
        data = bytes(row['content'])
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Stored image integrity check failed.')
        return data, 'image/png' if data.startswith(b'\x89PNG') else 'image/jpeg'

    def get(self, case_id):
        with connect(self.database) as db:
            row = db.execute('SELECT record_json FROM workflow_records WHERE case_id=?', (case_id,)).fetchone()
        if row is None:
            raise ValueError('Application not found in the local database.')
        return json.loads(row['record_json'])

    def list(self):
        with connect(self.database) as db:
            records = [json.loads(r['record_json']) for r in db.execute('SELECT record_json FROM workflow_records ORDER BY updated_at DESC')]
        return [{k: r[k] for k in ('case_id','order_id','status','updated_at')} for r in records]

    def _save(self, record, image_data=None):
        previous = record.get('updated_at')
        saved = json.loads(json.dumps(record))
        saved['updated_at'] = now()
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT updated_at FROM workflow_records WHERE case_id=?', (saved['case_id'],)).fetchone()
            if current is not None and current['updated_at'] != previous:
                raise ValueError('Application changed in another session. Reload before retrying.')
            if image_data is not None:
                db.execute('INSERT OR IGNORE INTO evidence_images VALUES (?,?)', (hashlib.sha256(image_data).hexdigest(), image_data))
            digest = saved['assessments'][-1].get('image_sha256')
            db.execute('INSERT INTO refund_cases VALUES (?,?,?,?,?) ON CONFLICT(case_id) DO UPDATE SET order_id=excluded.order_id, claim_text=excluded.claim_text, request_date=excluded.request_date, image_path=excluded.image_path',
                (saved['case_id'], saved['order_id'], saved['claim_text'], 'sqlite:sha256:'+digest if digest else 'NOT_STORED: historical upload', saved['request_date']))
            db.execute('INSERT INTO workflow_records VALUES (?,?,?) ON CONFLICT(case_id) DO UPDATE SET updated_at=excluded.updated_at, record_json=excluded.record_json',
                (saved['case_id'], saved['updated_at'], json.dumps(saved, ensure_ascii=False)))
        return saved
