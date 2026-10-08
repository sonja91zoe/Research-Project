"""Same-image, same-settings comparison; never replaces deployed weights."""
import hashlib
import json
import time
from pathlib import Path
import ultralytics
from ultralytics import YOLO


def main():
    root = Path(__file__).resolve().parents[1]
    human = json.loads((root/'data/external_test_pending/external_photo_human_review.json').read_text())['cases']
    assert len(human) == 12 and len({r['file'] for r in human}) == 12
    for row in human:
        assert row['confirmed'] is True
        assert hashlib.sha256((root/'data/external_test_pending'/row['file']).read_bytes()).hexdigest() == row['sha256']
    out = root/'artifacts'/('external_weight_comparison_'+time.strftime('%Y%m%d_%H%M%S'))
    out.mkdir()
    settings = dict(conf=0.01, imgsz=512, iou=0.7, max_det=300, device='cpu', augment=False, verbose=False)
    report = {'settings': settings, 'ultralytics': ultralytics.__version__, 'review_threshold':0.15,
              'limitations':'Image-level top-box label agreement with user labels; not box mAP or population accuracy. Discoloration excluded from two-class denominator. No clean controls. No deployment changes.', 'models':{}}
    paths = {'repository':'models/member2/best.pt',
             'local_training':'artifacts/member2_yolo_2026-10-08/damage_detector/weights/best.pt',
             'smoke':'artifacts/member2_yolo_smoke/damage_detector/weights/best.pt'}
    for name, relative in paths.items():
        model = YOLO(str(root/relative))
        assert model.names == {0:'hole_or_tear',1:'stain_or_spot'}, model.names
        folder = out/name
        folder.mkdir()
        rows = []
        started = time.monotonic()
        for row in human:
            result = model(str(root/'data/external_test_pending'/row['file']), **settings)[0]
            boxes = [{'label':result.names[int(b.cls.item())], 'score':float(b.conf.item()), 'xyxy':b.xyxy[0].tolist()} for b in result.boxes]
            best = max(boxes, key=lambda b:b['score']) if boxes else {'label':'uncertain','score':0.0}
            comparable = row['defect'] in model.names.values()
            rows.append(dict(file=row['file'],sha256=row['sha256'],human_label=row['defect'],prediction=best['label'],score=best['score'],
                             matches_human=(best['label']==row['defect']) if comparable else None,
                             review_flag=best['score']<0.15 or best['label']=='uncertain',boxes=boxes))
            result.save(filename=str(folder/row['file']))
        valid = [r for r in rows if r['matches_human'] is not None]
        summary = dict(correct=sum(r['matches_human'] for r in valid),comparable=len(valid),
                       review_flags=sum(r['review_flag'] for r in rows),
                       by_class={label:{'correct':sum(r['matches_human'] for r in valid if r['human_label']==label),'total':sum(r['human_label']==label for r in valid)} for label in model.names.values()},
                       seconds=time.monotonic()-started)
        report['models'][name] = dict(path=relative,sha256=hashlib.sha256((root/relative).read_bytes()).hexdigest(),summary=summary,results=rows)
        print(name,json.dumps(summary),flush=True)
        (out/'results.json').write_text(json.dumps(report,indent=2))
    lines = ['# Same-batch external photo comparison','',report['limitations'],'','| Model | Correct / comparable | Review flags / 12 |','|---|---|---|']
    for name,m in report['models'].items():
        s=m['summary']; lines.append(f"| {name} | {s['correct']}/{s['comparable']} | {s['review_flags']}/12 |")
    lines += ['', '| Photo | Human | Repository | Local training | Smoke |','|---|---|---|---|---|']
    for i,r in enumerate(human):
        cells=[f"{report['models'][n]['results'][i]['prediction']} ({report['models'][n]['results'][i]['score']:.3f})" for n in paths]
        lines.append('| '+ ' | '.join([r['file'],r['defect']]+cells)+' |')
    (out/'comparison.md').write_text('\n'.join(lines))
    print('OUTPUT',out,flush=True)


if __name__ == '__main__':
    main()
