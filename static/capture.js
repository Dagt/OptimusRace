/* Each athlete is saved independently. Polling never replaces an unsaved edit. */
if(q('#capture-list')){
 const list=q('#capture-list'),forms=qa('.capture-card',list),test=JSON.parse(q('#capture-test').textContent);
 const dirty=new Set(),saving=new Set(),remote=new Map();let filter='all',stale=false,polling=false;
 const saveButton=f=>q('[data-save-mark]',f);
 const feedback=(f,text,error=false)=>{const n=q('.save-feedback',f);n.textContent=text;n.className='save-feedback'+(error?' error':'')};
 function connection(text,ok){q('#network-status').replaceChildren(node('span',undefined,ok?'online-dot':'pending-dot'),document.createTextNode(text))}
 function render(){
  const term=q('#coach-search').value.trim().toLocaleLowerCase('es');const bib=/^#?\d+$/.test(term)?Number(term.replace('#','')):null;let visible=0;
  forms.forEach(f=>{f.hidden=!(bib!==null?Number(f.dataset.bib)===bib:f.dataset.search.toLocaleLowerCase('es').includes(term))||(filter==='pending'&&f.dataset.done==='1');if(!f.hidden)visible++});
  const complete=forms.filter(f=>f.dataset.done==='1').length;
  q('#capture-empty').hidden=visible>0;q('#capture-complete').textContent=complete;q('#pending-count').textContent=forms.length-complete;
  q('#capture-progress').style.width=`${forms.length?complete/forms.length*100:0}%`;
 }
 function preview(f){
  const done=f.elements.status.value==='done',locked=saving.has(f)||stale||f.dataset.enabled!=='1';
  for(const name of ['value','load','judged_points'])if(f.elements[name]){f.elements[name].disabled=locked||!done;f.elements[name].required=done}
  f.elements.status.disabled=locked;f.elements.reason.disabled=locked;
  saveButton(f).disabled=locked||f.dataset.conflict==='1';
  let points=null;
  if(test.scoring==='judge')points=done&&f.elements.judged_points.value!==''?Number(f.elements.judged_points.value):null;
  else if(test.scoring!=='relative'&&done&&f.elements.value.value!==''&&test.base!=null&&test.elite!=null&&test.elite!==test.base)
   points=(test.max_points??100)*Math.max(0,Math.min(1,.5+.5*(Number(f.elements.value.value)-test.base)/(test.elite-test.base)));
  q('.capture-preview strong',f).replaceChildren(document.createTextNode(!done?'Sin marca':test.scoring==='relative'?'Según categoría':points===null?'—':fmt(points)),node('span',done?(test.scoring==='relative'?'provisional':'pts'):''));
 }
 function applyMark(f,mark){
  f.elements.revision.value=mark.revision;
  f.elements.value.value=mark.value??'';if(f.elements.load)f.elements.load.value=mark.load??'';
  if(f.elements.judged_points)f.elements.judged_points.value=mark.points??'';
  f.elements.status.value=mark.revision?mark.status:'done';f.elements.reason.value='';
  f.dataset.done=mark.status==='done'?'1':'0';f.dataset.conflict='0';
  q('.correction-reason',f).hidden=!mark.revision;q('[data-load-saved]',f).hidden=true;
  saveButton(f).textContent=mark.revision?'Guardar corrección':'Guardar marca';
  paintScore(f,mark);preview(f);
 }
 function paintScore(f,mark){const state=q('.capture-state',f);state.className='capture-state'+(mark.status==='done'?' saved':'');state.textContent=mark.status==='done'?`${mark.points==null?'—':fmt(mark.points)} pts${mark.provisional?' · provisional':''}`:(stateNames[mark.status]||'Pendiente')}
 q('#coach-search').oninput=render;
 qa('button',q('#coach-filter')).forEach(b=>b.onclick=()=>{filter=b.dataset.filter;qa('button',q('#coach-filter')).forEach(x=>x.classList.toggle('selected',x===b));render()});
 forms.forEach(f=>{
  preview(f);
  f.addEventListener('input',()=>{dirty.add(f);feedback(f,'Cambios sin guardar');preview(f)});
  q('[data-load-saved]',f).onclick=()=>{
   if(dirty.has(f)&&!confirm('¿Descartar lo escrito en esta tarjeta y cargar la marca guardada en el servidor?'))return;
   const mark=remote.get(f);if(mark){dirty.delete(f);applyMark(f,mark);feedback(f,'Versión del servidor cargada.');render()}
  };
  f.addEventListener('submit',async event=>{
   event.preventDefault();if(stale||saving.has(f)||f.dataset.enabled!=='1'||f.dataset.conflict==='1')return;
   if(Number(f.elements.revision.value)>0&&!f.elements.reason.value.trim()){feedback(f,'Escribe el motivo de la corrección.',true);f.elements.reason.focus();return}
   const body=new FormData(f);saving.add(f);dirty.add(f);preview(f);saveButton(f).setAttribute('aria-busy','true');feedback(f,'Guardando…');
   try{
    const data=await jsonFetch(location.pathname,{method:'POST',body,headers:{'X-Requested-With':'XMLHttpRequest'}});
    dirty.delete(f);applyMark(f,{revision:data.revision,status:data.status,points:data.points,provisional:data.provisional,value:data.status==='done'?body.get('value'):null,load:data.status==='done'?body.get('load'):null});
    feedback(f,'Guardado confirmado · '+new Date().toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'}));q('.save-feedback',f).classList.add('success');
   }catch(error){feedback(f,error.name==='AbortError'?'No llegó la confirmación. Conservamos tus datos; consulta la versión guardada antes de reintentar.':error.message==='Failed to fetch'?'Sin conexión. Tus datos siguen en esta pantalla y todavía no están confirmados.':error.message,true)}
   finally{saving.delete(f);saveButton(f).removeAttribute('aria-busy');preview(f);render();poll()}
  });
 });
 async function poll(){
  if(polling||stale||document.hidden)return;polling=true;
  try{
   const data=await jsonFetch(list.dataset.liveUrl,{cache:'no-store'});connection('Sincronizado · '+new Date().toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'}),true);
   if(data.phase!=='live'||String(data.test_index)!==list.dataset.test){
    stale=true;q('#stale-stage').hidden=false;q('#stale-message').textContent=data.phase==='closed'?'El evento terminó. La captura está cerrada.':data.phase!=='live'?'La competencia aún no está en curso. Actualiza cuando administración la inicie.':'La estación activa cambió. Revisa tus datos pendientes antes de actualizar.';
    forms.forEach(preview);return;
   }
   const rows=new Map(data.board.map(row=>[String(row.id),row]));
   q('#roster-changed').hidden=rows.size===forms.length&&forms.every(f=>rows.has(f.elements.registration.value));
   forms.forEach(f=>{
    const row=rows.get(f.elements.registration.value),mark=row?.marks[Number(list.dataset.test)];
    f.dataset.enabled=row?.attendance==='present'?'1':'0';
    if(saving.has(f))return;
    if(mark){
     remote.set(f,mark);
     if(mark.revision>Number(f.elements.revision.value)){
      if(dirty.has(f)){f.dataset.conflict='1';q('[data-load-saved]',f).hidden=false;feedback(f,'Existe otra versión guardada. Tu captura pendiente se conserva; revisa la versión del servidor antes de corregir.',true)}
      else{applyMark(f,mark);feedback(f,'Actualizado desde el servidor.')}
     }else if(mark.revision===Number(f.elements.revision.value))paintScore(f,mark);
    }
    if(!row||row.attendance!=='present')feedback(f,'Captura bloqueada: revisa la inscripción o asistencia con administración.',true);
    preview(f);
   });render();
  }catch(error){connection(navigator.onLine?'Sin respuesta del servidor':'Sin conexión · no guardado',false)}
  finally{polling=false}
 }
 window.addEventListener('beforeunload',event=>{if(dirty.size||saving.size){event.preventDefault();event.returnValue=''}});
 window.addEventListener('offline',()=>connection('Sin conexión · no guardado',false));window.addEventListener('online',poll);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll()});
 render();connection('Comprobando conexión…',false);poll();setInterval(poll,5000);
}
