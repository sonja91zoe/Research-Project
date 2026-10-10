"use strict";
const $=id=>document.getElementById(id);
const show=(id,value)=>$(id).classList.toggle('hidden',!value);
async function api(path,payload){const response=await fetch(path,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await response.json();if(!response.ok)throw new Error(data.error||'Request failed');return data;}
function el(tag,text,className){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
function timestamp(value){return value?new Date(value).toLocaleString('en-AU'):'Unknown';}
function reason(record){const review=[...record.events].reverse().find(e=>['HUMAN_REJECT','HUMAN_REQUEST_MORE_EVIDENCE','HUMAN_APPROVE'].includes(e.action));return review?.note||record.assessments.at(-1)?.result.decision.reason||'';}
async function upload(input){const file=input.files[0];if(!file||!['image/jpeg','image/png'].includes(file.type)||file.size>8*1024*1024)throw new Error('Choose a JPG or PNG photo no larger than 8 MB.');return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('Unable to read the photo.'));reader.readAsDataURL(file);});}
let working=false;
async function task(fn,inference=false){if(working)return;working=true;$('message').textContent='';document.querySelectorAll('button').forEach(b=>b.disabled=true);if($('busy'))show('busy',inference);try{await fn();}catch(e){$('message').textContent=e.message;$('message').className='notice error';}finally{working=false;if($('busy'))show('busy',false);document.querySelectorAll('button').forEach(b=>b.disabled=false);}}
