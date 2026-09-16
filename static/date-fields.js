/* Day-first dates: type or paste digits; separators are inserted automatically. */
(()=>{
 function setup(input){if(input.dataset.dateReady)return;input.dataset.dateReady='1';const timed=input.placeholder.includes('HH:MM');input.inputMode='numeric';input.maxLength=timed?16:10;
  const format=value=>{if(/^\d{4}-\d{2}-\d{2}/.test(value)){const [d,t]=value.split('T');value=d.slice(8,10)+d.slice(5,7)+d.slice(0,4)+(t||'').replace(/\D/g,'').slice(0,4)}const digits=value.replace(/\D/g,'').slice(0,timed?12:8);return digits.slice(0,2)+(digits.length>2?'/'+digits.slice(2,4):'')+(digits.length>4?'/'+digits.slice(4,8):'')+(timed&&digits.length>8?' '+digits.slice(8,10):'')+(timed&&digits.length>10?':'+digits.slice(10,12):'')};
  if(input.value)input.value=format(input.value);
  input.addEventListener('beforeinput',event=>{const caret=input.selectionStart;if(event.inputType==='deleteContentBackward'&&caret===input.selectionEnd&&caret>0&&/[/ :]/.test(input.value[caret-1])){event.preventDefault();input.value=input.value.slice(0,caret-2)+input.value.slice(caret);input.setSelectionRange(caret-2,caret-2);input.dispatchEvent(new Event('input',{bubbles:true}))}});
  input.addEventListener('input',()=>{const position=input.selectionStart??input.value.length,count=input.value.slice(0,position).replace(/\D/g,'').length;input.value=format(input.value);let caret=0,seen=0;while(caret<input.value.length&&seen<count){if(/\d/.test(input.value[caret]))seen++;caret++}input.setSelectionRange(caret,caret);input.setCustomValidity('')});
  input.addEventListener('blur',()=>{if(!input.value)return;const m=input.value.match(timed?/^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/:/^(\d{2})\/(\d{2})\/(\d{4})$/),d=m?new Date(Date.UTC(+m[3],+m[2]-1,+m[1])):null;const valid=m&&d.getUTCDate()===+m[1]&&d.getUTCMonth()===+m[2]-1&&d.getUTCFullYear()===+m[3]&&(!timed||(+m[4]<24&&+m[5]<60));input.setCustomValidity(valid?'':'Escribe una fecha válida en día/mes/año'+(timed?' y hora HH:MM.':'.'))});
 }
 const scan=()=>document.querySelectorAll('input[placeholder^="dd/mm/"]').forEach(setup);scan();new MutationObserver(scan).observe(document.body,{childList:true,subtree:true});
})();
