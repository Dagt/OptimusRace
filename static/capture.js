/* Each athlete is saved independently. Polling never replaces an unsaved edit. */
if(q('#capture-list')){
 const list=q('#capture-list'),forms=qa('.capture-card',list),test=JSON.parse(q('#capture-test').textContent);
 const dirty=new Set(),saving=new Set(),remote=new Map();let filter='search',stale=false,polling=false,selected=null,optionsKey='';
 const resolved=f=>['done','absent','withdrawn'].includes(f.dataset.status)||['withdrawn','disqualified'].includes(f.dataset.attendance);
 const saveButton=f=>q('[data-save-mark]',f);
 const feedback=(f,text,error=false)=>{const n=q('.save-feedback',f);n.textContent=text;n.className='save-feedback'+(error?' error':'')};
 function connection(text,ok){q('#network-status').replaceChildren(node('span',undefined,ok?'online-dot':'pending-dot'),document.createTextNode(text))}
 function render(){
  const term=q('#coach-search').value.trim().toLocaleLowerCase('es');const bib=/^#?\d+$/.test(term)?Number(term.replace('#','')):null;
  const matches=forms.filter(f=>(filter!=='search'||term.length>0)&&(bib!==null?Number(f.dataset.bib)===bib:f.dataset.search.toLocaleLowerCase('es').includes(term))&&
   (filter!=='pending'||!resolved(f))&&(filter!=='done'||f.dataset.done==='1')&&(filter!=='drafts'||dirty.has(f)));
  const options=matches.map(f=>{
   const button=document.createElement('button');button.type='button';button.className='capture-option';
   button.setAttribute('aria-pressed',String(f===selected));button.dataset.registration=f.elements.registration.value;
   const status=saving.has(f)?'Guardando…':f.dataset.conflict==='1'?'Revisar conflicto':dirty.has(f)?'Sin guardar en este dispositivo':f.dataset.attendance==='withdrawn'?'Retirado del evento':f.dataset.attendance==='disqualified'?'Descalificado':f.dataset.status==='absent'?'No se presentó a esta prueba':f.dataset.done==='1'?'Realizada':'Por revisar';
   button.replaceChildren(node('strong',`#${String(f.dataset.bib).padStart(3,'0')} · ${f.dataset.name||f.dataset.search}`),node('span',status));
   button.onclick=()=>select(f);return button;
  });
  const key=JSON.stringify(options.map(b=>[b.dataset.registration,b.textContent,b.getAttribute('aria-pressed')]));
  if(key!==optionsKey){const focused=document.activeElement?.dataset.registration;q('#capture-options').replaceChildren(...options);optionsKey=key;if(focused)options.find(b=>b.dataset.registration===focused)?.focus()}
  forms.forEach(f=>{f.hidden=f!==selected});
  q('#capture-picker').hidden=filter==='search'&&(!term||!!selected);
  q('#capture-change').hidden=!selected;
  q('#capture-list-actions').hidden=filter==='search';
  qa('button',q('#coach-filter')).forEach(b=>{b.hidden=b.dataset.filter==='drafts'&&!dirty.size;b.setAttribute('aria-pressed',String(b.dataset.filter===filter))});
  q('#capture-page').textContent=`${matches.length} participantes en esta lista`;
  q('#capture-next-pending').disabled=!forms.some(f=>!resolved(f)&&f.dataset.enabled==='1');
  const complete=forms.filter(f=>f.dataset.done==='1').length,reviewed=forms.filter(resolved).length;
  q('#capture-empty').hidden=matches.length>0||(filter==='search'&&(!term||!!selected));q('#capture-complete').textContent=reviewed;q('#pending-count').textContent=forms.length-reviewed;
  q('#done-count').textContent=complete;q('#draft-count').textContent=dirty.size;
  q('#capture-progress').style.width=`${forms.length?reviewed/forms.length*100:0}%`;
 }
 function preview(f){
  const done=f.elements.status.value==='done',locked=saving.has(f)||stale||f.dataset.enabled!=='1';
  for(const name of ['value','load','judged_points'])if(f.elements[name]){f.elements[name].disabled=locked||!done;f.elements[name].required=done}
  f.elements.status.disabled=locked;f.elements.reason.disabled=locked;
  saveButton(f).disabled=locked||f.dataset.conflict==='1';

 }
 function applyMark(f,mark){
  f.elements.revision.value=mark.revision;
  f.elements.value.value=mark.value??'';if(f.elements.load)f.elements.load.value=mark.load??'';
  if(f.elements.judged_points)f.elements.judged_points.value=mark.points??'';
  f.elements.status.value=mark.revision?mark.status:'done';f.elements.reason.value='';
  f.dataset.status=mark.status;f.dataset.done=mark.status==='done'?'1':'0';f.dataset.conflict='0';
  q('.correction-reason',f).hidden=!mark.revision;q('[data-load-saved]',f).hidden=true;
  saveButton(f).textContent=mark.revision?'Guardar corrección':'Guardar marca';
  paintScore(f,mark);preview(f);
 }
 function paintScore(f,mark){const state=q('.capture-state',f);state.className='capture-state'+(mark.status==='done'?' saved':'');state.textContent=mark.status==='done'?`${mark.points==null?'—':fmt(mark.points)} pts${mark.provisional?' · provisional':''}`:(stateNames[mark.status]||'Pendiente')}
 function select(f){q('#capture-saved').hidden=true;selected=f;if(filter==='search')q('#coach-search').value='';render();q('.capture-identity',f).scrollIntoView?.({block:'nearest',behavior:'smooth'});if(filter==='search'&&!f.elements.value.disabled)f.elements.value.focus()}
 q('#coach-search').oninput=()=>{if(filter==='search')selected=null;render()};
 q('#coach-search').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();const options=q('#capture-options').children;if(options.length===1)options[0].onclick()}};
 q('#capture-change').onclick=()=>{selected=null;filter='search';q('#coach-search').value='';qa('button',q('#coach-filter')).forEach(b=>b.classList.toggle('selected',b.dataset.filter===filter));render();q('#coach-search').focus()};
 q('#capture-next-pending').onclick=()=>{const candidates=forms.filter(f=>!resolved(f)&&f.dataset.enabled==='1');if(!candidates.length)return;selected=candidates[(candidates.indexOf(selected)+1)%candidates.length];render();q('.capture-identity',selected).scrollIntoView?.({block:'nearest',behavior:'smooth'})};
 qa('button',q('#coach-filter')).forEach(b=>b.onclick=()=>{filter=b.dataset.filter;q('#coach-search').value='';qa('button',q('#coach-filter')).forEach(x=>x.classList.toggle('selected',x===b));render()});
 forms.forEach(f=>{
  f.reset();f.elements.test.value=list.dataset.test;preview(f);
  f.addEventListener('input',()=>{dirty.add(f);feedback(f,'Cambios sin guardar');preview(f);render()});
  q('[data-load-saved]',f).onclick=()=>{
   if(dirty.has(f)&&!confirm('¿Descartar lo escrito en esta tarjeta y cargar la marca guardada en el servidor?'))return;
   const mark=remote.get(f);if(mark){dirty.delete(f);applyMark(f,mark);feedback(f,'Versión del servidor cargada.');render()}
  };
  f.addEventListener('submit',async event=>{
   event.preventDefault();if(stale||saving.has(f)||f.dataset.enabled!=='1'||f.dataset.conflict==='1')return;
   if(Number(f.elements.revision.value)>0&&!f.elements.reason.value.trim()){feedback(f,'Escribe el motivo de la corrección.',true);f.elements.reason.focus();return}
   const body=new FormData(f);saving.add(f);dirty.add(f);preview(f);render();saveButton(f).setAttribute('aria-busy','true');feedback(f,'Guardando…');
   try{
    const data=await jsonFetch(location.pathname,{method:'POST',body,headers:{'X-Requested-With':'XMLHttpRequest'}});
    dirty.delete(f);applyMark(f,{revision:data.revision,status:data.status,points:data.points,provisional:data.provisional,value:data.status==='done'?body.get('value'):null,load:data.status==='done'?body.get('load'):null});
    feedback(f,'Guardado confirmado · '+new Date().toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'}));q('.save-feedback',f).classList.add('success');
    const confirmation=q('#capture-saved');confirmation.textContent=`Guardado · #${String(f.dataset.bib).padStart(3,'0')} · ${f.dataset.name||f.dataset.search}`;confirmation.hidden=false;
    if(selected===f){selected=null;render();if(filter==='search')q('#coach-search').focus();else q('#capture-next-pending').focus()}
   }catch(error){feedback(f,error.name==='AbortError'?'No llegó la confirmación. Conservamos tus datos; consulta la versión guardada antes de reintentar.':error.message==='Failed to fetch'?'Sin conexión. Tus datos siguen en esta pantalla y todavía no están confirmados.':error.message,true)}
   finally{saving.delete(f);saveButton(f).removeAttribute('aria-busy');preview(f);render();poll()}
  });
 });
 async function poll(){
  if(polling||document.hidden)return;polling=true;
  try{
   const data=await jsonFetch(list.dataset.liveUrl,{cache:'no-store'});connection('Sincronizado · '+new Date().toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'}),true);
   if(data.station_closed||data.phase!=='live'||String(data.test_index)!==list.dataset.test){
    stale=true;q('#stale-stage').hidden=false;q('#stale-message').textContent=data.station_closed?'Administración cerró esta estación. Las capturas guardadas se conservan. Actualiza si se reabre.':data.phase==='closed'?'El evento terminó. La captura está cerrada.':data.phase!=='live'?'La competencia aún no está en curso. Actualiza cuando administración la inicie.':'La estación activa cambió. Revisa tus datos pendientes antes de actualizar.';
    forms.forEach(preview);
    if(data.phase==='live'&&!data.station_closed&&String(data.test_index)!==list.dataset.test&&!dirty.size&&!saving.size){location.replace(location.pathname+'?station='+encodeURIComponent(data.test_index))}
    return;
   }
   stale=false;q('#stale-stage').hidden=true;
   const rows=new Map(data.board.map(row=>[String(row.id),row]));
   q('#roster-changed').hidden=rows.size===forms.length&&forms.every(f=>rows.has(f.elements.registration.value));
   forms.forEach(f=>{
    const row=rows.get(f.elements.registration.value),mark=row?.marks[Number(list.dataset.test)];
    f.dataset.attendance=row?.attendance||'pending';f.dataset.enabled=row&&!['withdrawn','disqualified'].includes(row.attendance)?'1':'0';
    q('[data-attendance-label]',f).textContent=row?.attendance==='pending'?'Asistencia aún sin comprobar':({present:'Presente',absent:'Ausente',withdrawn:'Retirado',disqualified:'Descalificado'}[row?.attendance]||'Sin inscripción');
    if(saving.has(f))return;
    if(mark){
     remote.set(f,mark);
     if(mark.revision>Number(f.elements.revision.value)){
      if(dirty.has(f)){f.dataset.conflict='1';q('[data-load-saved]',f).hidden=false;feedback(f,'Existe otra versión guardada. Tu captura pendiente se conserva; revisa la versión del servidor antes de corregir.',true)}
      else{applyMark(f,mark);feedback(f,'Actualizado desde el servidor.')}
     }else if(mark.revision===Number(f.elements.revision.value)){if(!dirty.has(f))applyMark(f,mark);else paintScore(f,mark)}
    }
    if(!row||['withdrawn','disqualified'].includes(row.attendance))feedback(f,'Captura bloqueada: revisa la inscripción o asistencia con administración.',true);
    preview(f);
   });render();
  }catch(error){connection(navigator.onLine?'Sin respuesta del servidor':'Sin conexión · no guardado',false)}
  finally{polling=false}
 }
 window.addEventListener('pageshow',event=>{
  if(!event.persisted&&!dirty.size&&!saving.size){forms.forEach(f=>{f.reset();f.elements.test.value=list.dataset.test;preview(f)})}
  if(event.persisted){stale=true;forms.forEach(preview)}
  poll();
 });
 window.addEventListener('beforeunload',event=>{if(dirty.size||saving.size){event.preventDefault();event.returnValue=''}});
 window.addEventListener('offline',()=>connection('Sin conexión · no guardado',false));window.addEventListener('online',poll);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll()});
 render();connection('Comprobando conexión…',false);poll();setInterval(poll,5000);
}
