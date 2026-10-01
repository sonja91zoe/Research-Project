'use strict';
const $ = id => document.getElementById(id);
const statusNames = {READY_TO_REFUND:'Ready to confirm simulated refund',NEEDS_EVIDENCE:'More evidence needed',PENDING_REVIEW:'Awaiting human review',REJECTED:'Not approved by reviewer',SIMULATED_REFUNDED:'Simulated refund completed'};
let current = null, orders = [], working = false, previewURL = null;
const show = (id, visible) => $(id).classList.toggle('hidden', !visible);
function message(text, error=false) { $('message').textContent=text; $('message').className=text ? 'notice '+(error?'error':'success'):''; }
async function api(path, payload) {
  const response = await fetch(path, payload===undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data = await response.json();
  if(!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
async function task(fn, inference=false) {
  if(working) return;
  working=true; message('');
  document.querySelectorAll('button').forEach(b=>b.disabled=true);
  if(inference){show('busy',true); $('step2').classList.add('active');}
  try{await fn();}catch(e){message(e.message,true);}finally{
    working=false;show('busy',false);document.querySelectorAll('button').forEach(b=>b.disabled=false);
    $('step2').classList.toggle('active',!!current);
  }
}
async function upload(input) {
  const file=input.files[0];
  if(!file || !['image/png','image/jpeg'].includes(file.type) || file.size>8*1024*1024) throw new Error('Choose a JPG or PNG photo no larger than 8 MB.');
  return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=()=>reject(new Error('Unable to read the photo'));r.readAsDataURL(file);});
}
function render(record) {
  current=record;show('newPanel',false);show('resultPanel',true);
  $('step1').classList.remove('active');$('step2').classList.add('active');$('step3').classList.add('active');
  $('status').textContent=statusNames[record.status]||record.status;
  $('caseInfo').textContent=`Order ${record.order_id} · Application ${record.case_id} · Date ${record.request_date}`;
  const assessment=record.assessments.at(-1), result=assessment.result;
  const notes={READY_TO_REFUND:'Automatic refund conditions were met, or a reviewer approved this application. Use the button below to complete the simulated refund.',NEEDS_EVIDENCE:'Upload another photo addressing the reason below. The previous record will be retained and the new evidence assessed.',PENDING_REVIEW:'The evidence or policy checks require human review. Record a review decision in the demonstration form below.',REJECTED:'The reviewer did not approve this application. The review note is saved in the application history.',SIMULATED_REFUNDED:'The workflow is complete. This is a simulated refund; no money was transferred.'};
  $('explanation').textContent=notes[record.status];
  $('reason').textContent='Original Agent decision: '+result.decision.reason;
  $('missing').textContent=result.missing_evidence.length ? 'Missing evidence: '+result.missing_evidence.map(x=>({detected_product:'product identity in the image',claim_image_consistency:'claim-image consistency',damage_location:'damage location'}[x]||x)).join(', ') : 'No missing fields were reported for this assessment.';
  $('evidence').textContent=JSON.stringify(result,null,2);
  $('resultImage').src=`/api/cases/${record.case_id}/images/${record.assessments.length-1}`;
  $('events').replaceChildren();
  for(const e of record.events){const li=document.createElement('li');li.textContent=`${new Date(e.at).toLocaleString('en-AU')} · ${e.action} · ${statusNames[e.status]||e.status}${e.reviewer?' · '+e.reviewer:''}${e.note?' — '+e.note:''}`;$('events').append(li);}
  show('evidenceForm',record.status==='NEEDS_EVIDENCE');show('reviewForm',record.status==='PENDING_REVIEW');show('confirmButton',record.status==='READY_TO_REFUND');
}
async function refresh(){
  const records=await api('/api/cases');$('records').replaceChildren();
  if(!records.length){const p=document.createElement('p');p.textContent='No applications yet';$('records').append(p);}
  for(const r of records){const b=document.createElement('button');b.className='record-button';b.disabled=working;b.textContent=`${r.order_id} · ${statusNames[r.status]} · ${r.case_id.slice(0,8)}`;b.onclick=()=>task(async()=>render(await api('/api/cases/'+r.case_id)));$('records').append(b);}
}
$('createForm').onsubmit=e=>{e.preventDefault();task(async()=>{
  const payload={order_id:$('order').value,claim_text:$('claim').value,request_date:$('requestDate').value,relevant_region_visible:$('visible').value==='true',confidence_method:$('method').value,image_base64:await upload($('image'))};
  render(await api('/api/cases',payload));await refresh();
},true);};
$('evidenceForm').onsubmit=e=>{e.preventDefault();task(async()=>{render(await api(`/api/cases/${current.case_id}/evidence`,{image_base64:await upload($('newImage')),relevant_region_visible:$('newVisible').value==='true'}));$('evidenceForm').reset();await refresh();},true);};
$('reviewForm').onsubmit=e=>{e.preventDefault();task(async()=>{render(await api(`/api/cases/${current.case_id}/review`,{reviewer:$('reviewer').value,note:$('reviewNote').value,action:$('reviewAction').value}));$('reviewForm').reset();await refresh();});};
$('confirmButton').onclick=()=>task(async()=>{render(await api(`/api/cases/${current.case_id}/confirm`,{}));await refresh();});
$('refresh').onclick=()=>task(refresh);
$('startOver').onclick=()=>{current=null;show('newPanel',true);show('resultPanel',false);$('createForm').reset();setDate();if(previewURL) URL.revokeObjectURL(previewURL);show('preview',false);$('orderInfo').textContent='';message('');$('step1').classList.add('active');$('step2').classList.remove('active');$('step3').classList.remove('active');};
$('image').onchange=()=>{if(previewURL) URL.revokeObjectURL(previewURL);const file=$('image').files[0];show('preview',!!file);if(file){previewURL=URL.createObjectURL(file);$('preview').src=previewURL;}};
$('order').onchange=()=>{const o=orders.find(x=>x.order_id===$('order').value);$('orderInfo').textContent=o?`Demo order · Amount ${o.price} · Purchase date ${o.purchase_date}`:'';};
function setDate(){const d=new Date();$('requestDate').value=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
setDate();task(async()=>{orders=await api('/api/orders');$('order').replaceChildren(new Option('Select a demo order',''));for(const o of orders)$('order').add(new Option(`${o.order_id} · ${o.product_name}`,o.order_id));await refresh();});
