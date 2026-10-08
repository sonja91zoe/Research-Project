"""Generate a local human review page; does not change orders or annotations."""
import json
import csv
from pathlib import Path


def attach_context(cases, root):
    with (root / 'data/Week4_damage_dataset_v1/damage_dataset_v1.csv').open(encoding='utf-8-sig', newline='') as stream:
        source_rows = list(csv.DictReader(stream))
    for case in cases:
        case['source_cases'] = [row for row in source_rows if row['source_image_id'] == case['source_image_id']]
        label = root / 'data/member2/week2/labels' / (Path(case['image_path']).stem + '.txt')
        case['label_file'] = str(label.relative_to(root)) if label.is_file() else None
        case['label_text'] = label.read_text() if label.is_file() else None
    return cases


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'data/evaluation/member3_primary_manifest.json').read_text())
    data = json.dumps(attach_context(manifest['cases'], root), ensure_ascii=False).replace('<', '\\u003c')
    page = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8">
<title>70 張衣物照片人工核對</title>
<style>body{font:17px system-ui;margin:24px;background:#f4f6fa;color:#182538}header{max-width:1100px;margin:auto}button,select,input{font:inherit;padding:9px;margin:6px;border:1px solid #bac4d4;border-radius:8px}button{cursor:pointer;background:#e5ecff}#grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;max-width:1100px;margin:24px auto}article{background:white;padding:16px;border-radius:14px}img{width:100%;height:350px;object-fit:contain}input{width:85%}small{display:block;color:#58677b}a{color:#2854a0}</style>
<header><h1>衣物照片人工核對</h1><p>請先看照片選類別，再勾選「已由我覆核」。看不清楚請選「未知」並填原因。這是人工標註，不是模型預測，也不能證明真實訂單。</p>
<p>不會自動修改訂單。請下載並保存結果；關閉頁面可能遺失未下載內容。可匯入先前下載的結果繼續。</p>
<button id="download">下載核對結果 JSON</button><label>匯入結果 <input type="file" id="import" accept=".json"></label><strong id="count"></strong></header><div id="grid"></div>
<script>const rows=DATA.map(x=>({...x,human_category:'',human_note:'',human_confirmed:false}));
const labels={'':'待確認','unknown':'未知／看不清','trousers':'長褲／運動褲','shorts':'短褲','t-shirt':'T-Shirt','shirt':'襯衫','top':'上衣（細分類不確定）','jacket':'外套','hoodie':'帽T','sweater':'毛衣','sweatshirt':'衛衣（無帽）','dress':'洋裝','skirt':'裙子','other':'其他（請備註）'};
function count(){document.querySelector('#count').textContent=`已覆核 ${rows.filter(x=>x.human_confirmed).length} / ${rows.length}`}
function render(){const grid=document.querySelector('#grid');grid.replaceChildren();for(const r of rows){const box=document.createElement('article');const title=document.createElement('h3');title.textContent=r.order_id+' · '+r.source_image_id;const img=document.createElement('img');img.src=r.image_path;img.loading='lazy';const link=document.createElement('a');link.href=r.image_path;link.target='_blank';link.textContent='開啟原圖放大';const select=document.createElement('select');for(const [v,t] of Object.entries(labels)){const o=new Option(t,v);select.add(o)}select.value=r.human_category;const note=document.createElement('input');note.placeholder='可見特徵／未知原因';note.value=r.human_note;const check=document.createElement('input');check.type='checkbox';check.style.width='auto';check.checked=r.human_confirmed;const label=document.createElement('label');label.append(check,'已由我覆核');select.onchange=()=>{r.human_category=select.value;r.human_confirmed=false;check.checked=false;count()};note.oninput=()=>{r.human_note=note.value;r.human_confirmed=false;check.checked=false;count()};check.onchange=()=>{if(check.checked&&(!r.human_category||(['unknown','other'].includes(r.human_category)&&!r.human_note.trim()))){alert('請選類別；未知／其他請填原因');check.checked=false}r.human_confirmed=check.checked;count()};box.append(title,img,link,document.createElement('br'),select,note,label);grid.append(box)}count()}
document.querySelector('#download').onclick=()=>{const data={review_method:'user_visual_review',scope:'garment_category_only_not_transaction_identity',cases:rows.map(r=>({order_id:r.order_id,image_sha256:r.image_sha256,human_category:r.human_category,human_note:r.human_note,human_confirmed:r.human_confirmed}))};const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='member3_human_photo_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
document.querySelector('#import').onchange=async e=>{try{const saved=JSON.parse(await e.target.files[0].text());if(!Array.isArray(saved.cases))throw Error('格式不符');const updates=[];const ids=new Set();for(const v of saved.cases){const r=rows.find(x=>x.order_id===v.order_id&&x.image_sha256===v.image_sha256);if(!r||ids.has(v.order_id)||!(v.human_category in labels)||typeof v.human_note!=='string'||typeof v.human_confirmed!=='boolean'||(v.human_confirmed&&(!v.human_category||(['unknown','other'].includes(v.human_category)&&!v.human_note.trim()))))throw Error('圖片版本或欄位不符');ids.add(v.order_id);updates.push([r,v])}for(const [r,v] of updates)Object.assign(r,{human_category:v.human_category,human_note:v.human_note,human_confirmed:v.human_confirmed});render()}catch(err){alert('無法匯入：'+err.message)}};render();</script></html>'''
    output = root / 'photo_review.html'
    context_js = '''function sourceContext(r){
      const details=document.createElement('details');
      const summary=document.createElement('summary');summary.textContent='查看原有案例與暫定標籤（不是模型答案）';details.append(summary);
      const warning=document.createElement('p');warning.textContent='先自行觀察，再展開標籤。100 個案例共用 70 張原圖；加工變體的標籤不能直接套用目前原圖。';details.append(warning);
      for(const c of r.source_cases){const p=document.createElement('p');p.style.whiteSpace='pre-wrap';p.textContent=c.case_id+'\\n描述：'+c.claim_text+'\\n暫定結果：'+c.expected_verdict+'\\n損壞類別：'+c.damage_type+'\\n覆核狀態：'+c.review_status+'\\n案例來源：'+c.case_origin+'\\n加工方式：'+c.construction_method;details.append(p)}
      const box=document.createElement('p');box.textContent=r.label_file?'找到本地 Week 2 同名標註檔（來源與座標對應尚未核實，不自動畫框）：'+r.label_file:'指定的 Week 2 標註目錄沒有同名檔案；不代表沒有破損。';details.append(box);
      if(r.label_file){const pre=document.createElement('pre');pre.style.whiteSpace='pre-wrap';pre.textContent=r.label_text||'空標註檔';details.append(pre)}
      return details;
    }
    '''
    page = page.replace('function render(){', context_js + 'function render(){')
    page = page.replace('grid.append(box)', 'box.append(sourceContext(r));grid.append(box)')
    output.write_text(page.replace('DATA', data), encoding='utf-8')
    print(output.name)


if __name__ == '__main__':
    main()
