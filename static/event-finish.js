(()=>{
document.querySelectorAll('[data-capacity-edit]').forEach(button=>button.onclick=()=>{const form=document.querySelector('#capacity-inline');form.hidden=!form.hidden;if(!form.hidden)form.querySelector('input[name="capacity"]').focus()});
const dialog=document.querySelector('#event-finish-dialog'),open=document.querySelector('[data-review-finish]');
if(!dialog||!open)return;
dialog.querySelector('[data-dismiss-finish]').onclick=()=>dialog.close();
open.onclick=async()=>{
 open.disabled=true;open.setAttribute('aria-busy','true');
 try{
  const response=await fetch(location.href,{cache:'no-store'});if(!response.ok)throw Error();
  const doc=new DOMParser().parseFromString(await response.text(),'text/html'),review=doc.querySelector('#event-finish-review');
  if(!review)throw Error();
  dialog.querySelector('#event-finish-review').replaceWith(review);dialog.querySelector('#finish-error').textContent='';
  const form=dialog.querySelector('form'),ack=form.querySelector('input[type=checkbox]');ack.addEventListener('change',()=>{form.querySelector('button').disabled=ack.disabled||!ack.checked});form.addEventListener('submit',()=>{form.querySelector('button').disabled=true;form.querySelector('button').textContent='Finalizando…'});
  dialog.showModal();
 }catch{dialog.querySelector('#finish-error').textContent='No se pudo actualizar la revisión. Cierra e intenta de nuevo.';dialog.querySelector('#event-finish-review').hidden=true;dialog.showModal()}
 finally{open.disabled=false;open.removeAttribute('aria-busy')}
};
})();
