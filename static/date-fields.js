/* Day-first dates: type or paste digits; separators are inserted automatically. */
(()=>{
 function setupTime(input){
  const required=input.required,disabled=input.disabled,initial=input.value;
  const group=document.createElement('span');group.className='datetime-picker';
  const title=input.closest('label')?.firstChild?.textContent?.trim()||'Fecha y hora';
  const date=document.createElement('input');date.type='date';date.min='1900-01-01';date.max='9999-12-31';date.setAttribute('aria-label',title+' · fecha');
  const hour=document.createElement('select'),minute=document.createElement('select');
  function options(select,count,caption){select.setAttribute('aria-label',title+' · '+caption);const blank=document.createElement('option');blank.value='';blank.textContent=caption;select.append(blank);for(let i=0;i<count;i++){const option=document.createElement('option');option.value=String(i).padStart(2,'0');option.textContent=option.value;select.append(option)}}
  options(hour,24,'Hora');options(minute,60,'Minutos');
  const calendar=document.createElement('span');calendar.className='datetime-date';calendar.append(date);
  const clock=document.createElement('span');clock.className='datetime-clock';const separator=document.createElement('span');separator.textContent=':';separator.setAttribute('aria-hidden','true');clock.append(hour,separator,minute);
  group.append(calendar,clock);
  let clear=null;if(!required){clear=document.createElement('button');clear.type='button';clear.className='text-button datetime-clear';clear.textContent='Limpiar';clear.setAttribute('aria-label','Limpiar '+title);group.append(clear)}
  input.type='hidden';input.required=false;input.after(group);
  function sync(notify=true){const any=!!(date.value||hour.value||minute.value);for(const field of [date,hour,minute]){field.required=required||any;field.disabled=disabled}if(clear){clear.disabled=disabled;clear.hidden=!any}
   date.setCustomValidity('');
   if(date.value&&hour.value!==''&&minute.value!==''){const [y,m,d]=date.value.split('-');input.value=`${d}/${m}/${y} ${hour.value}:${minute.value}`}else input.value='';
   if(notify)input.dispatchEvent(new Event('input',{bubbles:true}));
  }
  function load(value){const match=value.match(/^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/),iso=value.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);date.value=match?`${match[3]}-${match[2]}-${match[1]}`:iso?`${iso[1]}-${iso[2]}-${iso[3]}`:'';hour.value=match?match[4]:iso?iso[4]:'';minute.value=match?match[5]:iso?iso[5]:'';sync(false);if(value&&!input.value){date.setCustomValidity('Selecciona una fecha y una hora válidas.');input.value=value}}
  for(const field of [date,hour,minute])field.addEventListener('change',()=>sync());
  if(clear)clear.onclick=()=>{date.value=hour.value=minute.value='';sync()};
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
