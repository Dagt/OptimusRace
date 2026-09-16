/* Native event editor: all policy values travel through server validation. */
if(q('#config-form')){
 const form=q('#config-form'),original=JSON.parse(q('#initial-rules').textContent),catalog=JSON.parse(q('#catalog').textContent),modern=original.schema_version===2,caps=['Fuerza','Resistencia','Velocidad','Potencia'];
 function field(parent,label,value,type='text',options){const l=node('label',label),input=node(options?'select':'input');if(options)options.forEach(([v,t])=>{const o=node('option',t);o.value=v;input.append(o)});else{input.type=type;if(type==='number'){input.step='any';input.min=0}}input.value=value??'';l.append(input);parent.append(l);return input}
 const numeric=input=>input.value===''?null:Number(input.value);
 function removeButton(parent,remove){const b=node('button','Quitar','text-button');b.type='button';b.onclick=remove;parent.append(b)}
 const tests=[];let cats=[],prices=[],discounts=[];
 const auto=q('#auto-points');auto.checked=modern&&!(original.tests||[]).length;
 function distribute(){if(!tests.length)return;let used=0;tests.forEach((t,i)=>{const points=i===tests.length-1?100-used:Math.floor(1000000/tests.length)/10000;t.max.value=Number(points.toFixed(4));used+=points})}
 auto.onchange=()=>check();

 const specs=[['metric','Tipo de resultado',[['time','Tiempo'],['repetitions','Repeticiones'],['distance','Distancia / altura'],['weight','Peso'],['custom','Otra unidad']]],['duration_seconds','Duración del esfuerzo · seg'],['distance_meters','Distancia por recorrido · m'],['laps','Número de recorridos'],['load_mode','Carga',[['none','Sin carga'],['body_percent','% del peso corporal'],['fixed','Peso fijo · kg']]],['load_value','Carga · % o kg'],['bar_weight','Barra · kg'],['load_step','Incremento de carga · kg'],['round_mode','Redondeo',[['none','Sin redondeo'],['nearest','Más cercano'],['down','Hacia abajo'],['up','Hacia arriba']]],['precision','Decimales permitidos'],['min_value','Marca mínima válida'],['max_value','Marca máxima válida']];
 function check(){if(auto.checked)distribute();tests.forEach(t=>t.max.readOnly=auto.checked);q('#capacity-check').replaceChildren(node('span',`${tests.length} estaciones · ${fmt(tests.reduce((n,t)=>n+(numeric(t.max)||0),0))} / 100 puntos`),...caps.map(c=>node('span',`${c}: ${tests.filter(t=>t.capacity.value===c).length}`)))}
 function addTest(t={}){
  const row=node('details',undefined,'config-test');row.open=!t.name;
  const title=node('summary',undefined,'config-test-heading'),titleName=node('strong',t.name||'Nueva estación');title.append(titleName);row.append(title);
  const body=node('div',undefined,'config-test-body'),grid=node('div',undefined,'form-grid');body.append(grid);row.append(body);q('#test-editor').append(row);
  const select=field(grid,'Ejercicio del catálogo','','text',[['','Definir para este evento'],...catalog.map((c,i)=>[String(i),c.name])]);
  const name=field(grid,'Nombre',t.name),unit=field(grid,'Unidad de captura',t.unit??'reps'),capacity=field(grid,'Capacidad',t.capacity||caps[0],'text',caps.map(c=>[c,c])),higher=field(grid,'Mejor resultado',String(t.higher??true),'text',[['true','Mayor'],['false','Menor']]);
  const scoring=field(grid,'Evaluación',t.scoring||(!modern?'linear':'relative'),'text',[['relative','Relativa: mejor y peor de la categoría'],['pending','Seleccionar criterio'],['linear','Lineal: base 50%, élite 100%'],['judge','Puntos otorgados por juez']]);
  const max=field(grid,'Puntos máximos',t.max_points??(modern?1:12.5),'number'),base=field(grid,'Referencia base · 50% del máximo',t.base,'number'),elite=field(grid,'Referencia élite · 100% del máximo',t.elite,'number');
  const params={},p=t.parameters||{};specs.forEach(([key,label,options])=>params[key]=field(grid,label,p[key]??(key==='metric'?(t.name?'custom':'repetitions'):key==='load_mode'||key==='round_mode'?'none':''),options?'text':'number',options));
  const instructions=field(grid,'Protocolo / criterios de ejecución',p.instructions||''),equipment=field(grid,'Equipo permitido',p.equipment||'');
  const advanced=node('details',undefined,'exercise-section');advanced.append(node('summary','Personalizar prueba'));const advancedGrid=node('div',undefined,'form-grid');advanced.append(advancedGrid);body.append(advanced);
  for(const input of [unit,higher,scoring,max,base,elite,...Object.entries(params).filter(([k])=>k!=='metric').map(([,v])=>v),instructions,equipment])advancedGrid.append(input.parentElement);
  const summary=node('p',undefined,'measurement-summary');grid.append(summary);
  function describe(){summary.textContent=`Se registra en ${unit.value||'la unidad indicada'}. ${higher.value==='true'?'Mayor':'Menor'} marca es mejor. ${scoring.value==='relative'?'Puntos según los resultados de la categoría.':''}`}
  params.metric.addEventListener('change',()=>{const defaults={time:['seg','false'],repetitions:['reps','true'],distance:['cm','true'],weight:['kg','true']}[params.metric.value];if(defaults){unit.value=defaults[0];higher.value=defaults[1]}else advanced.open=true;describe()});
  [unit,higher,scoring].forEach(input=>input.addEventListener('change',describe));describe();
  const item={row,name,unit,capacity,higher,scoring,max,base,elite,params,instructions,equipment,source:t};tests.push(item);
  function loadFields(){for(const key of ['load_value','bar_weight','load_step','round_mode'])params[key].parentElement.hidden=params.load_mode.value==='none'}params.load_mode.onchange=loadFields;loadFields();
  function scoreFields(){base.parentElement.hidden=elite.parentElement.hidden=scoring.value!=='linear'}scoring.onchange=scoreFields;scoreFields();
  select.onchange=()=>{if(select.value==='')return;const c=catalog[Number(select.value)];name.value=c.name;unit.value=c.unit;capacity.value=c.capacity;higher.value=String(c.higher);base.value=c.base??'';elite.value=c.elite??'';const cp=c.parameters||{};specs.forEach(([key])=>params[key].value=cp[key]??(key==='metric'?(t.name?'custom':'repetitions'):key==='load_mode'||key==='round_mode'?'none':''));instructions.value=cp.instructions||'';equipment.value=cp.equipment||'';titleName.textContent=c.name;loadFields();describe();check()};
  name.oninput=()=>titleName.textContent=name.value;capacity.onchange=check;max.oninput=()=>{auto.checked=false;check()};
  const actions=node('div',undefined,'action-group');body.append(actions);
  for(const [label,delta] of [['Subir',-1],['Bajar',1]]){const b=node('button',label,'text-button');b.type='button';b.onclick=()=>{const i=tests.indexOf(item),j=i+delta;if(j<0||j>=tests.length)return;[tests[i],tests[j]]=[tests[j],tests[i]];tests.forEach(t=>q('#test-editor').append(t.row))};actions.append(b)}
  removeButton(actions,()=>{tests.splice(tests.indexOf(item),1);row.remove();check()});check();
 }
 (original.tests||[]).forEach(addTest);q('#add-test').onclick=()=>addTest();q('#equal-points').onclick=()=>{distribute();check()};check();
 function addCat(c={}){const row=node('div',undefined,'policy-row');q('#category-editor').append(row);const name=field(row,'Nombre',c.name),sex=field(row,'Categoría',c.sex||'M','text',[['M','Varonil'],['F','Femenil']]),min=field(row,'Desde · kg',c.min??0,'number'),max=field(row,'Hasta · kg (excluido)',c.max,'number');const item={name,sex,min,max};cats.push(item);removeButton(row,()=>{cats=cats.filter(i=>i!==item);row.remove()})}
 (original.categories||[]).forEach(addCat);q('#add-category').onclick=()=>addCat();
 // datetime-local is expressed in the venue's configured Mexico City timezone, not the browser's zone.
 function local(iso){return iso?new Intl.DateTimeFormat('sv-SE',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(iso)).replace(' ','T'):''}
 function iso(input){return input.value?input.value+':00-06:00':null}
 function addPrice(p={}){const row=node('div',undefined,'policy-row');q('#price-editor').append(row);const name=field(row,'Nombre de tarifa',p.name),amount=field(row,'Importe · MXN',p.amount==null?'':p.amount/100,'number'),start=field(row,'Desde (incluido)',local(p.start),'datetime-local'),end=field(row,'Hasta (excluido)',local(p.end),'datetime-local');amount.step='.01';const item={name,amount,start,end};prices.push(item);removeButton(row,()=>{prices=prices.filter(i=>i!==item);row.remove()})}
 (original.price_tiers||[]).forEach(addPrice);q('#add-price').onclick=()=>addPrice();
 function addDiscount(d={}){const row=node('div',undefined,'policy-row');q('#discount-editor').append(row);const code=field(row,'Código',d.code),kind=field(row,'Tipo',d.kind||'percent','text',[['percent','Porcentaje'],['fixed','Importe fijo · MXN']]),value=field(row,'Descuento · % o MXN',d.kind==='fixed'?d.value/100:d.value,'number'),limit=field(row,'Usos máximos (vacío = ilimitados)',d.limit,'number'),start=field(row,'Desde (opcional)',local(d.start),'datetime-local'),end=field(row,'Hasta (opcional)',local(d.end),'datetime-local');value.step='.01';limit.step='1';const item={code,kind,value,limit,start,end};discounts.push(item);removeButton(row,()=>{discounts=discounts.filter(i=>i!==item);row.remove()})}
 (original.discounts||[]).forEach(addDiscount);q('#add-discount').onclick=()=>addDiscount();
 form.addEventListener('input',()=>q('#config-status').textContent='Tienes cambios sin guardar.');
 form.addEventListener('submit',event=>{const data={...original,tests:tests.map(t=>{const parameters={...t.source.parameters,instructions:t.instructions.value,equipment:t.equipment.value};specs.forEach(([key,label,options])=>parameters[key]=options?t.params[key].value:numeric(t.params[key]));return {...t.source,name:t.name.value.trim(),unit:t.unit.value.trim(),capacity:t.capacity.value,higher:t.higher.value==='true',base:numeric(t.base),elite:numeric(t.elite),...(modern?{parameters,max_points:numeric(t.max),scoring:t.scoring.value}:{})}}),categories:cats.map(c=>({name:c.name.value.trim(),sex:c.sex.value,min:numeric(c.min),max:numeric(c.max)})),price_tiers:prices.map(p=>({name:p.name.value.trim(),amount:p.amount.value===''?null:Math.round(Number(p.amount.value)*100),start:iso(p.start),end:iso(p.end)})),discounts:discounts.map(d=>({code:d.code.value.trim().toUpperCase(),kind:d.kind.value,value:d.kind.value==='fixed'?(d.value.value===''?null:Math.round(Number(d.value.value)*100)):numeric(d.value),limit:numeric(d.limit),start:iso(d.start),end:iso(d.end)}))};q('#rules-input').value=JSON.stringify(data);q('#config-status').textContent='Guardando configuración…'});
 const pages=qa('[data-event-page]',form),steps=qa('[data-event-step]',form);let current=0;
 function showStep(index){current=Math.max(0,Math.min(pages.length-1,index));pages.forEach((page,i)=>page.hidden=i!==current);steps.forEach((button,i)=>{button.setAttribute('aria-current',i===current?'step':'false')});q('#previous-step').hidden=current===0;q('#next-step').hidden=current===pages.length-1;q('#step-progress').textContent=`Paso ${current+1} de ${pages.length}`}
 steps.forEach(button=>button.onclick=()=>showStep(Number(button.dataset.eventStep)));
 q('#previous-step').onclick=()=>showStep(current-1);q('#next-step').onclick=()=>showStep(current+1);
 function reveal(input){let ancestor=input.parentElement;while(ancestor&&ancestor!==form){if(ancestor.tagName==='DETAILS')ancestor.open=true;ancestor=ancestor.parentElement}const page=input.closest('[data-event-page]');if(page)showStep(Number(page.dataset.eventPage))}
 form.addEventListener('invalid',e=>reveal(e.target),true);
 const firstError=q('.errorlist',form);showStep(0);if(firstError)reveal(firstError);
 if(!modern){q('#add-test').disabled=true;q('#equal-points').disabled=true;toast('Edición con escala anterior: conserva sus reglas e historial. Los nuevos eventos usan parámetros por estación.')}
 if(form.dataset.locked==='1')qa('input,select,button,textarea',form).filter(n=>!n.matches('[data-event-step],#previous-step,#next-step')).forEach(n=>n.disabled=true);
}
