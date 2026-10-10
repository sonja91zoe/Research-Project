"""Run image-only inference; no training, order matching, or accuracy claims."""
import hashlib
import json
import time
from pathlib import Path

from src.damage_detection.runtime import resolve_yolo_weights
from src.damage_detection.damage import DEFAULT_REVIEW_THRESHOLD


def main():
    from ultralytics import YOLO

    root = Path(__file__).resolve().parents[1]
    weights = resolve_yolo_weights()
    output = root / 'artifacts' / ('external_image_test_' + time.strftime('%Y%m%d_%H%M%S'))
    output.mkdir(parents=True, exist_ok=False)
    model = YOLO(str(weights))
    started = time.monotonic()
    rows = []
    for path in sorted((root / 'data/external_test_pending').glob('*.png')):
        result = model(str(path), conf=0.01, device='cpu', verbose=False)[0]
        boxes = [{'class_id': int(b.cls.item()), 'label': result.names[int(b.cls.item())],
                  'score': float(b.conf.item()), 'xyxy': b.xyxy[0].tolist()}
                 for b in result.boxes]
        best = max(boxes, key=lambda b: b['score']) if boxes else None
        row = {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'prediction': best['label'] if best else 'uncertain',
               'score': best['score'] if best else 0.0,
               'damage_module_review': best is None or best['score'] < DEFAULT_REVIEW_THRESHOLD,
               'boxes': boxes}
        rows.append(row)
        result.save(filename=str(output / path.name))
        print(json.dumps({k: v for k, v in row.items() if k not in ('boxes', 'sha256')}), flush=True)
    report = {'weights': str(weights.relative_to(root)),
              'weights_sha256': hashlib.sha256(weights.read_bytes()).hexdigest(),
              'confidence_threshold': 0.01, 'review_threshold': DEFAULT_REVIEW_THRESHOLD,
              'seconds': time.monotonic() - started,
              'limitations': 'Image-only predictions, not calibrated probabilities or final refund decisions. No ground truth verified; accuracy not calculated.',
              'results': rows}
    (output / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('OUTPUT:', output, flush=True)
    print('SECONDS:', report['seconds'], flush=True)


if __name__ == '__main__':
    main()
