const KEY='nyf39_state_v2';
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
    {name:'Billionaire Index',why:'Rank and study wealth, operating leverage, power and contradiction',status:'watch'},
    {name:'Horn Founder Index',why:'Entrepreneurship across Somalia, Ethiopia, Eritrea, Djibouti, Kenya and the diaspora',status:'research'},
    {name:'Unsung Hero Index',why:'Civic courage, culture and overlooked impact worth archiving',status:'research'}
  ],
  dispatch:'',notes:[]
};
const stories=[
  {k:'01',title:'The 39 Day Arc',copy:'Transformation documented in real time: action, receipt, consequence, next move.'},
  {k:'02',title:'East Corner',copy:'Entrepreneurship, wealth, migration, culture and overlooked builders across the Horn and diaspora.'},
  {k:'03',title:'Follow the Money',copy:'Billionaires, millionaires, founders and institutions — what they built, how power compounds, and what the receipts reveal.'},
  {k:'04',title:'Unsung Heroes',copy:'People whose civic, cultural or economic impact deserves a brighter light and a better archive.'},
  {k:'05',title:'The Exposé',copy:'Investigate contradictions carefully. Separate allegation, evidence, response and what remains unknown.'},
  {k:'06',title:'New Scooby Van',copy:'The practical machine: tools, mobility, infrastructure and the physical systems that make the next chapter possible.'}
];
const $=s=>document.querySelector(s);
function fresh(){return JSON.parse(JSON.stringify(defaults))}
function load(){try{const raw=localStorage.getItem(KEY)||localStorage.getItem('nyf39_state_v1');return raw?{...fresh(),...JSON.parse(raw)}:fresh()}catch{return fresh()}}
let state=load();
function save(){localStorage.setItem(KEY,JSON.stringify(state));renderStats()}
const taskList=$('#taskList'), evidenceList=$('#evidenceList'), peopleList=$('#peopleList'), notesList=$('#notesList');
function renderTasks(){taskList.innerHTML='';state.tasks.forEach(t=>{const row=document.createElement('label');row.className='task'+(t.done?' done':'');row.innerHTML=`<input type="checkbox" ${t.done?'checked':''}><span></span><button class="delete" type="button">×</button>`;row.querySelector('span').textContent=t.text;row.querySelector('input').onchange=e=>{t.done=e.target.checked;save();renderTasks()};row.querySelector('.delete').onclick=()=>{state.tasks=state.tasks.filter(x=>x.id!==t.id);save();renderTasks()};taskList.appendChild(row)})}
function renderEvidence(){evidenceList.innerHTML=state.evidence.length?'':'<p class="muted">No receipts yet. Log the first one.</p>';[...state.evidence].reverse().forEach(e=>{const el=document.createElement('article');el.className='receipt';const d=new Date(e.time);el.innerHTML='<strong></strong><small></small><p></p>';el.querySelector('strong').textContent=e.title;el.querySelector('small').textContent=d.toLocaleString();el.querySelector('p').textContent=e.detail;evidenceList.appendChild(el)})}
function renderStories(){$('#storyGrid').innerHTML=stories.map(s=>`<article class="story"><span class="number">SERIES ${s.k}</span><h4>${s.title}</h4><p>${s.copy}</p><footer><span class="chip">active</span><button data-story="${s.k}">capture note →</button></footer></article>`).join('');document.querySelectorAll('[data-story]').forEach(b=>b.onclick=()=>openCapture('note',`Series ${b.dataset.story}: `))}
function renderPeople(){peopleList.innerHTML='';state.people.forEach((p,i)=>{const el=document.createElement('div');el.className='person';el.innerHTML=`<span class="rank">${String(i+1).padStart(2,'0')}</span><div><strong></strong><small></small></div><select><option>watch</option><option>research</option><option>draft</option><option>published</option></select>`;el.querySelector('strong').textContent=p.name;el.querySelector('small').textContent=p.why;el.querySelector('select').value=p.status;el.querySelector('select').onchange=e=>{p.status=e.target.value;save()};peopleList.appendChild(el)})}
function renderNotes(){notesList.innerHTML=state.notes.length?'':'<p class="muted">No story signals captured yet.</p>';[...state.notes].reverse().forEach(n=>{const el=document.createElement('article');el.className='note-card';el.innerHTML='<p></p><small></small>';el.querySelector('p').textContent=n.text;el.querySelector('small').textContent=new Date(n.time).toLocaleString();notesList.appendChild(el)})}
function renderStats(){const total=state.tasks.length||1,done=state.tasks.filter(t=>t.done).length;$('#executionScore').textContent=Math.round(done/total*100)+'%';$('#evidenceCount').textContent=state.evidence.length;$('#noteCount').textContent=state.notes.length;$('#dayNumber').textContent=String(state.day).padStart(2,'0')}
$('#taskForm').onsubmit=e=>{e.preventDefault();const input=$('#taskInput'),text=input.value.trim();if(!text)return;state.tasks.push({id:Date.now(),text,done:false});input.value='';save();renderTasks()};
$('#evidenceForm').onsubmit=e=>{e.preventDefault();const title=$('#evidenceTitle').value.trim(),detail=$('#evidenceDetail').value.trim();if(!title||!detail)return;state.evidence.push({title,detail,time:new Date().toISOString()});$('#evidenceTitle').value='';$('#evidenceDetail').value='';save();renderEvidence()};
$('#resetToday').onclick=()=>{state.tasks.forEach(t=>t.done=false);save();renderTasks()};
$('#advanceDay').onclick=()=>{if(state.day>=39)return alert('Day 39 is the end of this arc. Export the evidence before starting a new one.');if(!confirm(`Close Day ${state.day} and advance to Day ${state.day+1}?`))return;state.day++;state.tasks.forEach(t=>t.done=false);save();renderTasks()};
$('#addPerson').onclick=()=>{const name=prompt('Who are we tracking?');if(!name)return;const why=prompt('Why are they worth watching?')||'Watchlist';state.people.push({name,why,status:'watch'});save();renderPeople()};
$('#clearNotes').onclick=()=>{if(state.notes.length&&confirm('Clear captured story notes?')){state.notes=[];save();renderNotes()}};
const dispatch=$('#dispatchText');dispatch.value=state.dispatch;let timer;dispatch.oninput=()=>{clearTimeout(timer);$('#saveStatus').textContent='saving…';timer=setTimeout(()=>{state.dispatch=dispatch.value;save();$('#saveStatus').textContent='saved locally'},250)};
$('#copyDispatch').onclick=async()=>{await navigator.clipboard.writeText(dispatch.value);$('#copyDispatch').textContent='Copied';setTimeout(()=>$('#copyDispatch').textContent='Copy draft',1200)};
const dialog=$('#captureDialog');function openCapture(type='evidence',prefix=''){$('#captureType').value=type;$('#captureText').value=prefix;dialog.showModal();setTimeout(()=>$('#captureText').focus(),50)}
$('#quickAdd').onclick=()=>openCapture();
$('#captureSave').onclick=e=>{e.preventDefault();const type=$('#captureType').value,text=$('#captureText').value.trim();if(!text)return;if(type==='task')state.tasks.push({id:Date.now(),text,done:false});if(type==='evidence')state.evidence.push({title:text.split('\n')[0].slice(0,100),detail:text,time:new Date().toISOString()});if(type==='note')state.notes.push({text,time:new Date().toISOString()});save();renderTasks();renderEvidence();renderNotes();dialog.close()};
$('#exportData').onclick=()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`nyf-39-days-day-${String(state.day).padStart(2,'0')}.json`;a.click();URL.revokeObjectURL(url)};
$('#importData').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{const imported=JSON.parse(await file.text());state={...fresh(),...imported};save();renderAll();dispatch.value=state.dispatch||''}catch{alert('That backup file could not be read.')}e.target.value=''};
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCapture()}});
function renderAll(){renderTasks();renderEvidence();renderStories();renderPeople();renderNotes();renderStats()}
renderAll();