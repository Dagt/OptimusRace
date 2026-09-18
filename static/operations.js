// A saved station remains active across navigation; only a deliberate change submits.
qa('[data-station-switch]').forEach(form=>{
 const select=q('select[name="test"]',form),button=q('[data-station-submit]',form);
 function update(){const same=select.value===form.dataset.current;const open=form.dataset.captureClosed==='0';button.disabled=same||open||form.dataset.stale==='1';button.textContent=same?'Estación activa':open?'Primero cierra la captura actual':'Activar siguiente estación'}
 select.addEventListener('change',update);update();
 form.addEventListener('submit',event=>{
  if(select.value===form.dataset.current||form.dataset.stale==='1'||form.dataset.captureClosed==='0'||!confirm('¿Cambiar de estación para todos los coaches? Comprueba que hayan guardado sus capturas.')){event.preventDefault();return}
  button.disabled=true;button.textContent='Cambiando estación…';
 });
});
qa('[data-tie-form]').forEach(form=>{
 const selects=qa('select[name="member"]',form);
 function update(){const chosen=selects.map(s=>s.value).filter(Boolean);selects.forEach(s=>[...s.options].forEach(o=>{o.disabled=!!o.value&&o.value!==s.value&&chosen.includes(o.value)}))}
 selects.forEach(s=>s.addEventListener('change',update));update();
});
qa('.tie-list details').forEach(detail=>detail.addEventListener('toggle',()=>{
 if(detail.open)qa('.tie-list details').forEach(other=>{if(other!==detail)other.open=false});
}));
