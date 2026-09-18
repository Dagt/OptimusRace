/* One explicit state per capture: choose, camera, processing, review or error. */
qa('[data-photo-widget]').forEach(widget=>{
 const find=s=>q(s,widget),input=find('input[name="photo"]'),original=find('input[name="original_photo"]');
 const preview=find('[data-photo-preview]'),dialog=find('[data-photo-dialog]'),modalPreview=find('[data-photo-modal-preview]'),status=find('[data-photo-status]');
 const video=find('video'),stage=find('[data-camera-stage]'),sources=find('[data-photo-sources]');
 const open=find('[data-camera-open]'),capture=find('[data-camera-capture]'),back=find('[data-camera-close]'),use=find('[data-photo-use]'),retry=find('[data-photo-retry]'),discard=find('[data-photo-discard]');
 let state='choose',stream=null,generation=0,cameraGeneration=0,controller=null,raw=null,draftUrl=null;
 let savedFile=null,savedOriginal=null,savedPreview=preview.innerHTML,savedUrl=null;
 function attach(field,file){const transfer=new DataTransfer();if(file)transfer.items.add(file);field.files=transfer.files}
 function show(next,message){const nativePicker=!navigator.mediaDevices?.getUserMedia;widget.dataset.nativePicker=String(nativePicker);open.hidden=nativePicker;find('[data-photo-picker-label]').textContent=nativePicker?'Tomar o elegir foto':'Elegir archivo';find('.photo-dialog-footer').hidden=next==='choose'||next==='processing'||(next==='error'&&!raw);state=next;widget.dataset.captureState=next;stage.hidden=next!=='camera';sources.hidden=!['choose','error'].includes(next);modalPreview.hidden=next!=='review';capture.hidden=back.hidden=next!=='camera';use.hidden=next!=='review';use.disabled=next!=='review';retry.hidden=next!=='error'||!raw;discard.hidden=!['review','error'].includes(next)||!raw;status.textContent=nativePicker&&next==='choose'?'':message}
 function stopCamera(){cameraGeneration++;stream?.getTracks().forEach(track=>track.stop());stream=null;video.srcObject=null}
 function cancelRequest(){generation++;controller?.abort();controller=null}
 function releaseDraft(){if(draftUrl&&draftUrl!==savedUrl)URL.revokeObjectURL(draftUrl);draftUrl=null}
 function restore(){cancelRequest();stopCamera();releaseDraft();raw=null;attach(input,savedFile);attach(original,savedOriginal);preview.innerHTML=savedPreview;modalPreview.replaceChildren();show('choose','Abre la cámara o elige una foto.')}
 find('[data-photo-open]').onclick=()=>{restore();dialog.showModal()};
 find('[data-photo-cancel]').onclick=()=>{restore();dialog.close()};
 dialog.addEventListener('cancel',event=>{event.preventDefault();restore();dialog.close()});
 dialog.addEventListener('close',()=>{if(state!=='choose')restore();stopCamera()});
 async function process(file){cancelRequest();stopCamera();releaseDraft();raw=file;const current=generation;show('processing','Preparando retrato deportivo…');
  if(file.size>5*1024*1024||!['image/jpeg','image/png','image/webp'].includes(file.type)){show('error','Elige JPG, PNG o WebP de hasta 5 MB.');raw=null;retry.hidden=true;return}
  controller=new AbortController();const body=new FormData();body.append('photo',file);body.append('csrfmiddlewaretoken',q('[name="csrfmiddlewaretoken"]',input.form).value);
  try{const response=await fetch(widget.dataset.portraitUrl,{method:'POST',body,credentials:'same-origin',signal:controller.signal});if(!response.ok){let message='No se pudo procesar la foto. Intenta otra vez.';try{message=(await response.json()).error||message}catch{}throw new Error(message)}if(!response.headers.get('content-type')?.startsWith('image/'))throw new Error('Tu sesión terminó. Vuelve a iniciar sesión.');const blob=await response.blob();if(current!==generation)return;draftUrl=URL.createObjectURL(blob);const img=new Image();img.src=draftUrl;img.alt='Vista previa del retrato deportivo';modalPreview.replaceChildren(img);show('review','Revisa el retrato. Usa esta foto o toma otra.')}
  catch(error){if(current===generation&&error.name!=='AbortError')show('error',error.message)}
 }
 input.addEventListener('change',()=>{if(input.files[0])process(input.files[0])});retry.onclick=()=>{if(raw)process(raw)};discard.onclick=restore;
 open.onclick=async()=>{if(!navigator.mediaDevices?.getUserMedia){input.click();return}cancelRequest();stopCamera();const current=++cameraGeneration;show('processing','Abriendo cámara…');
  try{const acquired=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:1280}},audio:false});if(current!==cameraGeneration){acquired.getTracks().forEach(track=>track.stop());return}stream=acquired;video.srcObject=stream;await video.play();if(current!==cameraGeneration)return;show('camera','Centra rostro y hombros. Pulsa Capturar foto cuando esté listo.')}
  catch{if(current!==cameraGeneration)return;stopCamera();show('error','No se pudo abrir la cámara. Revisa el permiso o elige un archivo.')}
 };
 capture.onclick=()=>{if(!video.videoWidth||state!=='camera')return;const current=cameraGeneration,canvas=document.createElement('canvas'),scale=Math.min(1,1400/Math.max(video.videoWidth,video.videoHeight));canvas.width=Math.round(video.videoWidth*scale);canvas.height=Math.round(video.videoHeight*scale);canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);capture.disabled=true;canvas.toBlob(blob=>{capture.disabled=false;if(current===cameraGeneration&&blob)process(new File([blob],'captura.jpg',{type:'image/jpeg'}))},'image/jpeg',.94)};
 back.onclick=restore;
 use.onclick=()=>{if(state!=='review'||!raw||!draftUrl)return;if(savedUrl&&savedUrl!==draftUrl)URL.revokeObjectURL(savedUrl);savedUrl=draftUrl;savedFile=raw;savedOriginal=raw;attach(input,raw);attach(original,raw);preview.innerHTML=modalPreview.innerHTML;savedPreview=preview.innerHTML;raw=null;show('choose','Foto lista para guardar.');stopCamera();dialog.close()};
 input.form.addEventListener('submit',event=>{if(state!=='choose'){event.preventDefault();event.stopImmediatePropagation();if(!dialog.open)dialog.showModal();status.textContent='Confirma o descarta la captura antes de guardar.';return}stopCamera()},true);
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&state==='camera'){stopCamera();show('choose','La cámara se cerró al cambiar de ventana. Puedes abrirla de nuevo.')}});
 window.addEventListener('pagehide',()=>{stopCamera();cancelRequest()});show('choose','Abre la cámara o elige una foto.');
});
qa('[data-photo-launch]').forEach(button=>button.onclick=()=>q('[data-photo-open]').click());
