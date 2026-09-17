/* Availability, countdowns and explicit, user-initiated camera capture. */
qa('[data-countdown]').forEach(panel=>{
 const target=Date.parse(panel.dataset.countdown),server=Date.parse(panel.dataset.serverNow),offset=Number.isFinite(server)?server-Date.now():0;
 if(!Number.isFinite(target))return;
 function tick(){const total=Math.max(0,Math.ceil((target-Date.now()-offset)/1000));const values={days:Math.floor(total/86400),hours:Math.floor(total/3600)%24,minutes:Math.floor(total/60)%60,seconds:total%60};for(const [key,value] of Object.entries(values))q(`[data-time="${key}"]`,panel).textContent=String(value).padStart(2,'0');if(!total){q('[data-countdown-status]',panel).textContent='Llegó la hora programada. Consulta el estado del evento.';return false}return true}
 tick();const timer=setInterval(()=>{if(!tick())clearInterval(timer)},1000);
});
qa('[data-availability-url]').forEach(panel=>{
 async function refresh(){try{const data=await jsonFetch(panel.dataset.availabilityUrl,{cache:'no-store'});qa('[data-seat]',panel).forEach(item=>item.textContent=data[item.dataset.seat]);q('[data-seat-progress]',panel).style.width=(data.capacity?Math.min(100,100*data.occupied/data.capacity):0)+'%';q('[data-seat-feedback]',panel).textContent=data.full?'Cupo agotado.':data.registration_open?'Inscripción en mostrador con pago en efectivo.':'Inscripciones cerradas o aún no abiertas.'}catch{q('[data-seat-feedback]',panel).textContent='No se pudo actualizar el cupo. Se muestra la última información disponible.'}}
 setInterval(()=>{if(!document.hidden)refresh()},20000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});
});
