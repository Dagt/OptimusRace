// Refresh only standings, never the surrounding correction forms or event controls.
qa('[data-standings-url]').forEach(panel=>{
 let busy=false,lastHTML=null;
 const status=node('p','Los resultados se actualizan cada 5 segundos.','standings-sync');
 status.setAttribute('role','status');panel.before(status);
 async function refresh(){
  if(busy||document.hidden||!panel.getClientRects().length)return;
  busy=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
  try{
   const response=await fetch(panel.dataset.standingsUrl,{cache:'no-store',signal:controller.signal});
   if(!response.ok)throw new Error('No se pudo consultar');
   const html=await response.text(),parsed=new DOMParser().parseFromString(html,'text/html'),replacement=q('.event-results-stack',parsed);
   if(!replacement)throw new Error('Respuesta inválida');
   if(html!==lastHTML){
    // Do not interrupt keyboard focus, selected text or an expanded capacity table.
    const selection=window.getSelection();
    if(selection&&!selection.isCollapsed&&panel.contains(selection.anchorNode))return;
    const active=panel.contains(document.activeElement)?document.activeElement:null;
    const focusedSummary=active?.tagName==='SUMMARY'?active.textContent.trim():null;
    const focusedHref=active?.tagName==='A'?active.getAttribute('href'):null;
    const opened=qa('details[open]',panel).map(d=>q('summary',d).textContent.trim());
    panel.replaceChildren(...replacement.childNodes);
    qa('details',panel).forEach(d=>d.open=opened.includes(q('summary',d).textContent.trim()));
    const focusTarget=focusedSummary?qa('summary',panel).find(n=>n.textContent.trim()===focusedSummary):focusedHref?qa('a',panel).find(n=>n.getAttribute('href')===focusedHref):null;
    focusTarget?.focus({preventScroll:true});
    qa('.completion-dots[data-completed]',panel).forEach(n=>n.replaceWith(dots(Number(n.dataset.completed),Number(n.dataset.total)||8)));
    lastHTML=html;
   }
   status.textContent='Resultados sincronizados · '+new Date().toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'});
  }catch{status.textContent='Sin actualización del servidor. Se conservan los últimos resultados recibidos.'}
  finally{clearTimeout(timeout);busy=false}
 }
 document.addEventListener('visibilitychange',refresh);window.addEventListener('online',refresh);
 setInterval(refresh,5000);refresh();
});

// Keep the current station count fresh without replacing the administrator's form.
qa('[data-station-progress]').forEach(label=>{
 let busy=false;
 async function refresh(){
  if(busy||document.hidden)return;busy=true;
  try{
   const data=await jsonFetch(label.dataset.source,{cache:'no-store'});
   qa('[data-tie-count]').forEach(n=>n.textContent=data.pending_ties??0);qa('[data-tie-alert]').forEach(n=>n.hidden=!data.pending_ties);
   if(data.phase!=='live'||String(data.test_index)!==label.dataset.test){label.textContent='El estado o la estación cambiaron en otra pantalla. Actualiza este resumen.';qa('[data-station-switch]').forEach(f=>{f.dataset.stale='1';q('[data-station-submit]',f).disabled=true});return}
   const done=data.board.filter(row=>row.marks[Number(label.dataset.test)]?.status==='done').length;
   label.textContent=`${done} de ${data.board.length} participantes con esta prueba realizada`;
  }catch{label.textContent='No se pudo actualizar el avance. Revisa la conexión antes de cambiar de estación.'}
  finally{busy=false}
 }
 setInterval(refresh,5000);refresh();
});
