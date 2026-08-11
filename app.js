const KEY='nyf39_state_v1';
const defaults={
  day:1,
  tasks:[
    {id:1,text:'Admin: complete the highest-stakes call or submission',done:false},
    {id:2,text:'Body: complete today’s 39 Days movement block',done:false},
    {id:3,text:'Business: move NYF Holdings forward one material step',done:false},
    {id:4,text:'Evidence: log one receipt that proves the day changed',done:false}
  ],
  evidence:[],
  people:[
    {name:'Builder 001',why:'Billionaire / operator watchlist',status:'watch'},
    {name:'Horn Founder 001',why:'Entrepreneurship across the Horn',status:'research'},
    {name:'Unsung Hero 001',why:'Culture, civic courage, overlooked impact',status:'research'}
  ],
  dispatch:'',
  notes:[]
};
const stories=[
  {k:'01',title:'The 39 Day Arc',copy:'Daily transformation as documented evidence — not aspiration, not retrospective mythology.'},
  {k:'02',title:'The East Corner',copy:'Entrepreneurship, wealth, culture and overlooked builders across the Horn and its diaspora.'},
  {k:'03',title:'The Exposé',copy:'Follow power closely: founders, millionaires, billionaires, institutions, contradictions and receipts.'},
  {k:'04',title:'Unsung Heroes',copy:'People whose civic, cultural or economic impact deserves a brighter light and a better archive.'}
];
let state=load();
function load(){try{return {...defaults,...JSON.parse(localStorage.getItem(KEY)||'{}')}}catch{return structuredClone(defaults)}}
function save(){localStorage.setItem(KEY,JSON.stringify(state));renderStats()}
const $=s=>document.querySelector(s);
const taskList=$('#taskList'), evidenceList=$('#evidenceList'), peopleList=$('#peopleList');
function renderTasks(){
  taskList.innerHTML='';
  state.tasks.forEach(t=>{
    const row=document.createElement('label'); row.className='task'+(t.done?' done':'');
    row.innerHTML=`<input type="checkbox" ${t.done?'checked':''}><span></span><button class="delete" type="button">×</button>`;
    row.querySelector('span').textContent=t.text;
    row.querySelector('input').onchange=e=>{t.done=e.target.checked;save();renderTasks()};
    row.querySelector('.delete').onclick=()=>{state.tasks=state.tasks.filter(x=>x.id!==t.id);save();renderTasks()};
    taskList.appendChild(row);
  });
}
function renderEvidence(){
  evidenceList.innerHTML=state.evidence.length?'':'<p class="muted">No receipts yet. Log the first one.</p>';
  [...state.evidence].reverse().forEach(e=>{
    const el=document.createElement('article'); el.className='receipt';
    const d=new Date(e.time);
    el.innerHTML='<strong></strong><small></small><p></p>';
    el.querySelector('strong').textContent=e.title;
    el.querySelector('small').textContent=d.toLocaleString();
    el.querySelector('p').textContent=e.detail;
    evidenceList.appendChild(el);
  });
}
function renderStories(){
  $('#storyGrid').innerHTML=stories.map(s=>`<article class="story"><span class="number">SERIES ${s.k}</span><h4>${s.title}</h4><p>${s.copy}</p><footer><span class="chip">active</span><button data-story="${s.k}">capture note →</button></footer></article>`).join('');
  document.querySelectorAll('[data-story]').forEach(b=>b.onclick=()=>openCapture('note',`Series ${b.dataset.story}: `));
}
function renderPeople(){
  peopleList.innerHTML='';
  state.people.forEach((p,i)=>{
    const el=document.createElement('div'); el.className='person';
    el.innerHTML=`<span class="rank">${String(i+1).padStart(2,'0')}</span><div><strong></strong><small></small></div><select><option>watch</option><option>research</option><option>draft</option><option>published</option></select>`;
    el.querySelector('strong').textContent=p.name; el.querySelector('small').textContent=p.why; el.querySelector('select').value=p.status;
    el.querySelector('select').onchange=e=>{p.status=e.target.value;save()};
    peopleList.appendChild(el);
  });
}
function renderStats(){
  const total=state.tasks.length||1, done=state.tasks.filter(t=>t.done).length;
  $('#executionScore').textContent=Math.round(done/total*100)+'%';
  $('#evidenceCount').textContent=state.evidence.length;
  $('#dayNumber').textContent=String(state.day).padStart(2,'0');
  $('#storyCount').textContent=stories.length;
}
$('#taskForm').onsubmit=e=>{e.preventDefault();const input=$('#taskInput');const text=input.value.trim();if(!text)return;state.tasks.push({id:Date.now(),text,done:false});input.value='';save();renderTasks()};
$('#evidenceForm').onsubmit=e=>{e.preventDefault();const title=$('#evidenceTitle').value.trim(),detail=$('#evidenceDetail').value.trim();if(!title||!detail)return;state.evidence.push({title,detail,time:new Date().toISOString()});$('#evidenceTitle').value='';$('#evidenceDetail').value='';save();renderEvidence()};
$('#resetToday').onclick=()=>{state.tasks.forEach(t=>t.done=false);save();renderTasks()};
$('#addPerson').onclick=()=>{const name=prompt('Who are we tracking?');if(!name)return;const why=prompt('Why are they worth watching?')||'Watchlist';state.people.push({name,why,status:'watch'});save();renderPeople()};
const dispatch=$('#dispatch');dispatch.value=state.dispatch;let timer;dispatch.oninput=()=>{clearTimeout(timer);$('#saveStatus').textContent='saving…';timer=setTimeout(()=>{state.dispatch=dispatch.value;save();$('#saveStatus').textContent='saved locally'},250)};
$('#copyDispatch').onclick=async()=>{await navigator.clipboard.writeText(dispatch.value);$('#copyDispatch').textContent='Copied';setTimeout(()=>$('#copyDispatch').textContent='Copy draft',1200)};
const dialog=$('#captureDialog');
function openCapture(type='evidence',prefix=''){ $('#captureType').value=type;$('#captureText').value=prefix;dialog.showModal();setTimeout(()=>$('#captureText').focus(),50)}
$('#quickAdd').onclick=()=>openCapture();
$('#captureSave').onclick=e=>{e.preventDefault();const type=$('#captureType').value,text=$('#captureText').value.trim();if(!text)return;if(type==='task')state.tasks.push({id:Date.now(),text,done:false});if(type==='evidence')state.evidence.push({title:text.split('\n')[0].slice(0,100),detail:text,time:new Date().toISOString()});if(type==='note')state.notes.push({text,time:new Date().toISOString()});save();renderTasks();renderEvidence();dialog.close()};
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCapture()}});
renderTasks();renderEvidence();renderStories();renderPeople();renderStats();
