/* Day-first dates: type or paste digits; separators are inserted automatically. */
(()=>{
 function setupTime(input){
  const required=input.required,disabled=input.disabled,initial=input.value;
  const group=document.createElement('span');group.className='datetime-picker';
  const title=input.closest('label')?.firstChild?.textContent?.trim()||'Fecha y hora';
  const date=document.createElement('input');date.type='text';date.placeholder='dd/mm/aaaa';date.setAttribute('aria-label',title+' · día/mes/año');setup(date);
  const time=document.createElement('input');time.type='text';time.placeholder='HH:MM';time.inputMode='numeric';time.maxLength=5;time.setAttribute('aria-label',title+' · hora de 24 horas');
  const picker=document.createElement('input');picker.type='date';picker.setAttribute('aria-label','Abrir calendario · '+title);picker.disabled=disabled;
  const calendar=document.createElement('span');calendar.className='datetime-date';
  const trigger=document.createElement('span');trigger.className='datetime-calendar';const icon=document.createElement('span');icon.textContent='▦';icon.setAttribute('aria-hidden','true');trigger.append(icon,picker);calendar.append(date,trigger);
  const clock=document.createElement('span');clock.className='datetime-clock';clock.append(time);group.append(calendar,clock);
  let clear=null;if(!required){clear=document.createElement('button');clear.type='button';clear.className='text-button datetime-clear';clear.textContent='Limpiar';clear.setAttribute('aria-label','Limpiar '+title);group.append(clear)}
  input.type='hidden';input.required=false;input.after(group);
  function sync(notify=true){const any=!!(date.value||time.value);for(const field of [date,time]){field.required=required||any;field.disabled=disabled}if(clear){clear.disabled=disabled;clear.hidden=!any}
   const m=date.value.match(/^(\d{2})\/(\d{2})\/(\d{4})$/),d=m?new Date(Date.UTC(+m[3],+m[2]-1,+m[1])):null;
   const validDate=m&&d.getUTCDate()===+m[1]&&d.getUTCMonth()===+m[2]-1&&d.getUTCFullYear()===+m[3];
   const validTime=/^([01]\d|2[0-3]):[0-5]\d$/.test(time.value);
   date.setCustomValidity(!date.value||validDate?'':'Usa una fecha válida: día/mes/año.');
   time.setCustomValidity(!time.value||validTime?'':'Usa una hora de 00:00 a 23:59.');
   picker.value=validDate?`${m[3]}-${m[2]}-${m[1]}`:'';
   input.value=validDate&&validTime?`${date.value} ${time.value}`:'';
   if(notify)input.dispatchEvent(new Event('input',{bubbles:true}));
  }
  function load(value){const match=value.match(/^(\d{2}\/\d{2}\/\d{4}) (\d{2}:\d{2})$/),iso=value.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}:\d{2})/);date.value=match?match[1]:iso?`${iso[3]}/${iso[2]}/${iso[1]}`:'';time.value=match?match[2]:iso?iso[4]:'';sync(false);if(value&&!input.value){date.setCustomValidity('Selecciona una fecha y una hora válidas.');input.value=value}}
  date.addEventListener('input',()=>sync());date.addEventListener('change',()=>sync());
  time.addEventListener('input',()=>{const digits=time.value.replace(/\D/g,'').slice(0,4);time.value=digits.slice(0,2)+(digits.length>2?':'+digits.slice(2):'');sync()});
  time.addEventListener('change',()=>sync());
  picker.addEventListener('change',()=>{const [y,m,d]=picker.value.split('-');date.value=y&&m&&d?`${d}/${m}/${y}`:'';sync()});
  if(clear)clear.onclick=()=>{date.value=time.value='';sync()};
  input.form?.addEventListener('reset',()=>setTimeout(()=>load(initial),0));load(initial);
 }
 function setup(input){if(input.dataset.dateReady)return;input.dataset.dateReady='1';const timed=input.placeholder.includes('HH:MM');if(timed){setupTime(input);return}input.inputMode='numeric';input.maxLength=timed?16:10;
  const format=value=>{if(/^\d{4}-\d{2}-\d{2}/.test(value)){const [d,t]=value.split('T');value=d.slice(8,10)+d.slice(5,7)+d.slice(0,4)+(t||'').replace(/\D/g,'').slice(0,4)}const digits=value.replace(/\D/g,'').slice(0,timed?12:8);return digits.slice(0,2)+(digits.length>2?'/'+digits.slice(2,4):'')+(digits.length>4?'/'+digits.slice(4,8):'')+(timed&&digits.length>8?' '+digits.slice(8,10):'')+(timed&&digits.length>10?':'+digits.slice(10,12):'')};
  if(input.value)input.value=format(input.value);
  input.addEventListener('beforeinput',event=>{const caret=input.selectionStart;if(event.inputType==='deleteContentBackward'&&caret===input.selectionEnd&&caret>0&&/[/ :]/.test(input.value[caret-1])){event.preventDefault();input.value=input.value.slice(0,caret-2)+input.value.slice(caret);input.setSelectionRange(caret-2,caret-2);input.dispatchEvent(new Event('input',{bubbles:true}))}});
  input.addEventListener('input',()=>{const position=input.selectionStart??input.value.length,count=input.value.slice(0,position).replace(/\D/g,'').length;input.value=format(input.value);let caret=0,seen=0;while(caret<input.value.length&&seen<count){if(/\d/.test(input.value[caret]))seen++;caret++}input.setSelectionRange(caret,caret);input.setCustomValidity('')});
  input.addEventListener('blur',()=>{if(!input.value)return;const m=input.value.match(timed?/^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/:/^(\d{2})\/(\d{2})\/(\d{4})$/),d=m?new Date(Date.UTC(+m[3],+m[2]-1,+m[1])):null;const valid=m&&d.getUTCDate()===+m[1]&&d.getUTCMonth()===+m[2]-1&&d.getUTCFullYear()===+m[3]&&(!timed||(+m[4]<24&&+m[5]<60));input.setCustomValidity(valid?'':'Escribe una fecha válida en día/mes/año'+(timed?' y hora HH:MM.':'.'))});
 }
 const scan=()=>document.querySelectorAll('input[placeholder^="dd/mm/"]').forEach(setup);scan();new MutationObserver(scan).observe(document.body,{childList:true,subtree:true});
})();
