(()=>{
const manager=document.querySelector('.station-manager');
if(manager){
 const search=manager.querySelector('#station-search'),filter=manager.querySelector('#station-filter'),rows=[...manager.querySelectorAll('.station-row')],dialog=manager.querySelector('#station-team');
 const feedback=manager.querySelector('#station-feedback');let busy=false;
 const render=()=>{if(!search)return;rows.forEach(row=>row.hidden=!(row.dataset.stationName.toLocaleLowerCase('es').includes(search.value.trim().toLocaleLowerCase('es'))&&(filter.value==='all'||(filter.value==='open')===(row.dataset.stationOpen==='1'))));manager.querySelector('#station-empty').hidden=rows.some(row=>!row.hidden)};
 if(search){search.addEventListener('input',render);filter.addEventListener('change',render)}
 const forms=dialog?[...dialog.querySelectorAll('[data-assignment-coach]')]:[];
 const updateButtons=()=>forms.forEach(form=>{const same=form.dataset.current===dialog.dataset.station;form.elements.test.value=same?'':dialog.dataset.station;form.querySelector('button').textContent=same?'Retirar':form.dataset.current?'Mover aquí':'Asignar'});
 if(dialog){
  const coachSearch=dialog.querySelector('#coach-search-assignment');
  manager.querySelectorAll('[data-assign-station]').forEach(button=>button.addEventListener('click',()=>{dialog.querySelector('#station-team-title').textContent=button.dataset.name;dialog.dataset.station=button.dataset.assignStation;coachSearch.value='';forms.forEach(form=>form.hidden=false);updateButtons();dialog.showModal();coachSearch.focus()}));
  dialog.querySelector('[data-close-team]').onclick=()=>dialog.close();coachSearch.oninput=()=>forms.forEach(form=>form.hidden=!form.dataset.assignmentCoach.toLocaleLowerCase('es').includes(coachSearch.value.toLocaleLowerCase('es')));
 }
 function apply(data){
  for(const station of data.stations||[]){
   const row=rows.find(r=>Number(r.dataset.stationId)===station.test);if(!row)continue;
   row.dataset.stationOpen=station.open?'1':'0';const form=row.querySelector('[data-station-toggle]');
   form.dataset.pending=station.pending;form.elements.revision.value=station.revision;form.elements.enabled.value=station.open?'0':'1';
   form.querySelector('button').setAttribute('aria-checked',String(station.open));form.querySelector('small').textContent=station.label;
   row.querySelector('.station-count strong').textContent=station.done+'/'+row.querySelector('.station-count strong').textContent.split('/')[1];
   row.querySelector('.station-count small').textContent=station.pending+' pendientes';
   const assigned=(data.assignments||[]).filter(a=>a.test===station.test),summary=row.querySelector('.station-coach-summary');
   summary.textContent=assigned.length===1?assigned[0].name:assigned.length?assigned.length+' coaches':'Sin asignar';summary.title=assigned.map(a=>a.name).join(', ');
  }
  for(const form of forms){const a=(data.assignments||[]).find(a=>String(a.coach)===form.dataset.coachId);form.dataset.current=a?.test==null?'':String(a.test);form.elements.revision.value=a?.revision||0;form.querySelector('small').textContent=a?.station_name||'Sin estación asignada'}
  updateButtons();
  const badge=document.querySelector('.page-heading .badge');if(badge&&data.phase==='live'){badge.textContent='En competencia';badge.className='badge live'}
 }
 manager.querySelectorAll('[data-station-toggle],[data-assignment-coach]').forEach(form=>form.addEventListener('submit',async event=>{
  event.preventDefault();if(busy)return;
  busy=true;const button=form.querySelector('button');button.disabled=true;button.setAttribute('aria-busy','true');feedback.textContent='';dialog?.querySelector('[data-team-status]')?.remove();
  try{
   const response=await fetch(location.pathname,{method:'POST',body:new FormData(form),headers:{'X-Requested-With':'XMLHttpRequest'},cache:'no-store'});
   if(!response.headers.get('content-type')?.includes('application/json'))throw Error('No se pudo confirmar el cambio. Revisa tu sesión e intenta de nuevo.');
   const data=await response.json();apply(data);if(!response.ok||!data.ok)throw Error(data.error||'No se pudo guardar.');
   feedback.textContent='Cambios guardados.';
  }catch(error){feedback.textContent=error.message==='Failed to fetch'?'Sin conexión. No se pudo confirmar el cambio; intenta de nuevo.':error.message;const status=dialog?.querySelector('[data-team-status]');if(dialog?.open){if(status)status.textContent=feedback.textContent;else{const message=document.createElement('p');message.dataset.teamStatus='';message.setAttribute('role','alert');message.textContent=feedback.textContent;dialog.append(message)}}}
  finally{busy=false;button.disabled=false;button.removeAttribute('aria-busy')}
 }));
}
const waiting=document.querySelector('#coach-waiting');if(waiting){const poll=async()=>{try{const response=await fetch(waiting.dataset.source,{cache:'no-store'});if(response.ok){const data=await response.json();if(!data.unassigned&&data.phase!=='closed'){location.reload();return}}}catch{}setTimeout(poll,5000)};poll()}
})();