(()=>{
const manager=document.querySelector('.station-manager');
if(manager){
 const search=manager.querySelector('#station-search'),filter=manager.querySelector('#station-filter'),rows=[...manager.querySelectorAll('.station-row')];
 const render=()=>{rows.forEach(row=>row.hidden=!(row.dataset.stationName.toLocaleLowerCase('es').includes(search.value.trim().toLocaleLowerCase('es'))&&(filter.value==='all'||(filter.value==='open')===(row.dataset.stationOpen==='1'))));manager.querySelector('#station-empty').hidden=rows.some(row=>!row.hidden)};
 if(search){search.addEventListener('input',render);filter.addEventListener('change',render)}
 manager.querySelectorAll('[data-station-toggle]').forEach(form=>form.addEventListener('submit',event=>{if(form.elements.enabled.value==='0'&&Number(form.dataset.pending)>0&&!confirm(`Quedan ${form.dataset.pending} participantes pendientes. ¿Pausar la captura? Las marcas se conservan.`))event.preventDefault()}));
 const stateKey='station-controls:'+location.pathname;
 const dialog=manager.querySelector('#station-team');if(dialog){
 const forms=[...dialog.querySelectorAll('[data-assignment-coach]')],coachSearch=dialog.querySelector('#coach-search-assignment');
 manager.querySelectorAll('[data-assign-station]').forEach(button=>button.addEventListener('click',()=>{dialog.querySelector('#station-team-title').textContent=button.dataset.name;coachSearch.value='';forms.forEach(form=>{form.hidden=false;const same=form.dataset.current===button.dataset.assignStation;form.elements.test.value=same?'':button.dataset.assignStation;form.querySelector('button').textContent=same?'Retirar':form.dataset.current?'Mover aquí':'Asignar'});dialog.dataset.station=button.dataset.assignStation;dialog.showModal();coachSearch.focus()}));
 dialog.querySelector('[data-close-team]').onclick=()=>dialog.close();coachSearch.oninput=()=>forms.forEach(form=>form.hidden=!form.dataset.assignmentCoach.toLocaleLowerCase('es').includes(coachSearch.value.toLocaleLowerCase('es')));
 }
 if(search){
  manager.querySelectorAll('form').forEach(form=>form.addEventListener('submit',event=>{
   if(event.defaultPrevented)return;
   try{sessionStorage.setItem(stateKey,JSON.stringify({search:search.value,filter:filter.value,top:window.scrollY,table:manager.querySelector('.station-table').scrollTop,dialog:form.hasAttribute('data-assignment-coach')?dialog.dataset.station:null}))}catch{}
  }));
  try{const saved=JSON.parse(sessionStorage.getItem(stateKey)||'null');sessionStorage.removeItem(stateKey);if(saved){search.value=saved.search;filter.value=saved.filter;render();manager.querySelector('.station-table').scrollTop=saved.table;requestAnimationFrame(()=>window.scrollTo(0,saved.top));if(saved.dialog!==null)manager.querySelector(`[data-assign-station="${Number(saved.dialog)}"]`)?.click()}}catch{}
 }
}
const waiting=document.querySelector('#coach-waiting');if(waiting){const poll=async()=>{try{const response=await fetch(waiting.dataset.source,{cache:'no-store'});if(response.ok){const data=await response.json();if(!data.unassigned&&data.phase!=='closed'){location.reload();return}}}catch{}setTimeout(poll,5000)};poll()}
})();