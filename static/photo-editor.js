/* Reception capture: one automatic sports portrait, no original-background option. */
qa('[data-photo-widget]').forEach(widget=>{
 const find=s=>q(s,widget),input=find('input[name="photo"]'),original=find('input[name="original_photo"]'),preview=find('[data-photo-preview]'),initial=preview.innerHTML,status=find('[data-photo-status]'),stage=find('[data-camera-stage]'),video=find('video'),open=find('[data-camera-open]'),retry=find('[data-photo-retry]'),discard=find('[data-photo-discard]');
 const dialog=find('[data-photo-dialog]'),modalPreview=find('[data-photo-modal-preview]'),use=find('[data-photo-use]');let savedPhoto=null,savedOriginal=null,savedPreview=initial;
 function restore(){cancel();stop();raw=null;ready=true;attach(input,savedPhoto);attach(original,savedOriginal);preview.innerHTML=savedPreview;modalPreview.replaceChildren();use.disabled=true;retry.hidden=discard.hidden=true}
 find('[data-photo-open]').onclick=()=>{dialog.showModal();status.textContent='Toma una foto o elige un archivo.'};
 find('[data-photo-cancel]').onclick=()=>{restore();dialog.close()};dialog.addEventListener('cancel',event=>{event.preventDefault();restore();dialog.close()});
 use.onclick=()=>{if(use.disabled)return;savedPhoto=input.files[0]||null;savedOriginal=original.files[0]||null;preview.innerHTML=modalPreview.innerHTML;savedPreview=preview.innerHTML;ready=true;stop();dialog.close()};
 let stream=null,version=0,cameraVersion=0,controller=null,raw=null,ready=true,url=null,urls=[];
 const attach=(field,file)=>{const transfer=new DataTransfer();if(file)transfer.items.add(file);field.files=transfer.files};
 function stop(){cameraVersion++;stream?.getTracks().forEach(track=>track.stop());stream=null;video.srcObject=null;stage.hidden=true;open.disabled=false}
 function cancel(){version++;controller?.abort();controller=null}
 async function process(file){cancel();const current=version;stop();raw=file;ready=false;use.disabled=true;retry.hidden=true;discard.hidden=false;
  if(file.size>5*1024*1024||!['image/jpeg','image/png','image/webp'].includes(file.type)){status.textContent='Elige JPG, PNG o WebP de hasta 5 MB.';return}
  status.textContent='Preparando acabado deportivo… La primera vez puede tardar mientras se prepara el modelo.';
  controller=new AbortController();const body=new FormData();body.append('photo',file);body.append('csrfmiddlewaretoken',q('[name="csrfmiddlewaretoken"]',input.form).value);
  try{const response=await fetch(widget.dataset.portraitUrl,{method:'POST',body,credentials:'same-origin',signal:controller.signal});if(!response.ok){let message='No se pudo procesar la foto. Intenta de nuevo.';try{message=(await response.json()).error||message}catch{}throw new Error(message)}if(!response.headers.get('content-type')?.startsWith('image/'))throw new Error('La sesión terminó. Vuelve a iniciar sesión antes de tomar la foto.');const blob=await response.blob();if(current!==version)return;attach(input,file);attach(original,file);url=URL.createObjectURL(blob);urls.push(url);const img=new Image();img.src=url;img.alt='Retrato deportivo listo para guardar';modalPreview.replaceChildren(img);use.disabled=false;status.textContent='Revisa el retrato y pulsa Usar esta foto. Si no te gusta, toma otra.'}
  catch(error){if(current===version&&error.name!=='AbortError'){status.textContent=error.message;retry.hidden=false}}
 }
 input.addEventListener('change',()=>{if(input.files[0])process(input.files[0])});retry.onclick=()=>{if(raw)process(raw)};
 discard.onclick=()=>{restore();status.textContent='Se conserva la foto anterior. Puedes tomar otra.'};
 open.onclick=async()=>{if(!navigator.mediaDevices?.getUserMedia){status.textContent='La cámara necesita HTTPS o localhost. Puedes elegir un archivo.';return}stop();const current=++cameraVersion;open.disabled=true;try{const acquired=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:1280}},audio:false});if(current!==cameraVersion){acquired.getTracks().forEach(track=>track.stop());return}stream=acquired;video.srcObject=stream;stage.hidden=false;await video.play();status.textContent='Centra rostro y hombros, y pulsa Capturar foto.'}catch{stop();status.textContent='No se pudo abrir la cámara. Revisa el permiso o elige un archivo.'}};
 find('[data-camera-capture]').onclick=()=>{if(!video.videoWidth)return;const current=cameraVersion,canvas=document.createElement('canvas'),scale=Math.min(1,1400/Math.max(video.videoWidth,video.videoHeight));canvas.width=Math.round(video.videoWidth*scale);canvas.height=Math.round(video.videoHeight*scale);canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);canvas.toBlob(blob=>{if(current===cameraVersion&&blob)process(new File([blob],'captura.jpg',{type:'image/jpeg'}))},'image/jpeg',.92)};
 find('[data-camera-close]').onclick=stop;
 input.form.addEventListener('submit',event=>{if(!ready){event.preventDefault();event.stopImmediatePropagation();status.textContent='Revisa y confirma la foto antes de guardar.';if(!dialog.open)dialog.showModal();return}stop()},true);
 dialog.addEventListener('close',()=>{if(!ready)restore();stop()});widget.closest('dialog')?.addEventListener('close',stop);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop()});window.addEventListener('pagehide',()=>{stop();cancel();urls.forEach(value=>URL.revokeObjectURL(value))});
});

qa('[data-photo-launch]').forEach(button=>button.onclick=()=>q('[data-photo-open]').click());
