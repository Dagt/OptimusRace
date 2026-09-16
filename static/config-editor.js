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

 function check(){if(auto.checked)distribute();tests.forEach(t=>t.max.readOnly=auto.checked);q('#capacity-check').replaceChildren(node('span',`${tests.length} estaciones · ${fmt(tests.reduce((n,t)=>n+(numeric(t.max)||0),0))} / 100 puntos`),...caps.map(c=>node('span',`${c}: ${tests.filter(t=>t.source.capacity===c).length}`)))}
 function addTest(t={}){
  const row=node('section',undefined,'config-test'),body=node('div',undefined,'config-test-body'),grid=node('div',undefined,'form-grid');body.append(grid);row.append(body);q('#test-editor').append(row);
  const title=node('h3',t.name||'Selecciona una prueba');body.prepend(title);
  const choice=field(grid,'Prueba del catálogo','','text',[['',t.name?'Conservar prueba guardada':'Selecciona una prueba'],...catalog.map((c,i)=>[String(i),c.name])]);choice.required=!t.name;
  const scoring=field(grid,'Cómo asignar puntos',t.scoring||(!modern?'linear':'relative'),'text',[['relative','Según mejor y peor de la categoría'],['judge','Puntos capturados por el juez'],['linear','Referencias fijas']]);
  const max=field(grid,'Puntos de esta prueba',t.max_points??1,'number');max.min='.01';
  const base=field(grid,'Solo referencias fijas: marca para 50%',t.base,'number'),elite=field(grid,'Solo referencias fijas: marca para 100%',t.elite,'number');
  const description=node('p',undefined,'measurement-summary');body.append(description);
  const item={row,choice,scoring,max,base,elite,source:{...t}};tests.push(item);
  function summarize(){const c=item.source,p=c.parameters||{};title.textContent=c.name||'Selecciona una prueba';description.textContent=c.name?[c.capacity,`El juez registra ${c.unit}`,c.higher?'Mayor marca es mejor':'Menor marca es mejor',p.duration_seconds?`${p.duration_seconds} s de esfuerzo`:'',p.distance_meters?`${p.distance_meters} m × ${p.laps||1} recorridos`:'',p.load_mode==='body_percent'?`Carga: ${p.load_value}% corporal`:p.load_mode==='fixed'?`Carga: ${p.load_value} kg`:'',p.instructions||''].filter(Boolean).join(' · '):'Crea primero el ejercicio en el catálogo. Aquí no tienes que volver a definirlo.'}
  function scoreFields(){base.disabled=elite.disabled=scoring.value!=='linear';base.required=elite.required=scoring.value==='linear'}scoring.onchange=scoreFields;scoreFields();
  choice.onchange=()=>{if(choice.value===''){item.source={...t};choice.required=!t.name}else{item.source=structuredClone(catalog[Number(choice.value)]);choice.required=false;item.source.max_points=numeric(max)}base.value=item.source.base??'';elite.value=item.source.elite??'';summarize();check()};
  max.oninput=()=>{auto.checked=false;check()};
  const actions=node('div',undefined,'action-group');body.append(actions);
  for(const [label,delta] of [['Subir',-1],['Bajar',1]]){const button=node('button',label,'text-button');button.type='button';button.onclick=()=>{const i=tests.indexOf(item),j=i+delta;if(j<0||j>=tests.length)return;[tests[i],tests[j]]=[tests[j],tests[i]];tests.forEach(entry=>q('#test-editor').append(entry.row))};actions.append(button)}
  removeButton(actions,()=>{tests.splice(tests.indexOf(item),1);row.remove();check()});summarize();check();
 }
 (original.tests||[]).forEach(addTest);q('#add-test').onclick=()=>addTest();q('#equal-points').onclick=()=>{distribute();check()};check();
 function addCat(c={}){const row=node('div',undefined,'policy-row');q('#category-editor').append(row);const name=field(row,'Nombre',c.name),sex=field(row,'Categoría',c.sex||'M','text',[['M','Varonil'],['F','Femenil']]),min=field(row,'Desde · kg',c.min??0,'number'),max=field(row,original.category_bounds==='upper_inclusive'?'Hasta · kg (incluido)':'Hasta · kg (excluido)',c.max,'number');const item={name,sex,min,max};cats.push(item);removeButton(row,()=>{cats=cats.filter(i=>i!==item);row.remove()})}
 (original.categories||[]).forEach(addCat);q('#add-category').onclick=()=>addCat();
 // datetime-local is expressed in the venue's configured Mexico City timezone, not the browser's zone.
 function local(iso){return iso?new Intl.DateTimeFormat('sv-SE',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(iso)).replace(' ','T'):''}
 function iso(input){return input.value?input.value+':00-06:00':null}
 function addPrice(p={}){const row=node('div',undefined,'policy-row');q('#price-editor').append(row);const name=field(row,'Nombre de tarifa',p.name),amount=field(row,'Importe · MXN',p.amount==null?'':p.amount/100,'number'),start=field(row,'Desde (incluido)',local(p.start),'datetime-local'),end=field(row,'Hasta (excluido)',local(p.end),'datetime-local');amount.step='.01';const item={name,amount,start,end};prices.push(item);removeButton(row,()=>{prices=prices.filter(i=>i!==item);row.remove()})}
 (original.price_tiers||[]).forEach(addPrice);q('#add-price').onclick=()=>addPrice();
 function addDiscount(d={}){const row=node('div',undefined,'policy-row');q('#discount-editor').append(row);const code=field(row,'Código',d.code),kind=field(row,'Tipo',d.kind||'percent','text',[['percent','Porcentaje'],['fixed','Importe fijo · MXN']]),value=field(row,'Descuento · % o MXN',d.kind==='fixed'?d.value/100:d.value,'number'),limit=field(row,'Usos máximos (vacío = ilimitados)',d.limit,'number'),start=field(row,'Desde (opcional)',local(d.start),'datetime-local'),end=field(row,'Hasta (opcional)',local(d.end),'datetime-local');value.step='.01';limit.step='1';const item={code,kind,value,limit,start,end};discounts.push(item);removeButton(row,()=>{discounts=discounts.filter(i=>i!==item);row.remove()})}
 (original.discounts||[]).forEach(addDiscount);q('#add-discount').onclick=()=>addDiscount();
 form.addEventListener('input',()=>q('#config-status').textContent='Tienes cambios sin guardar.');
 form.addEventListener('submit',event=>{const data={...original,tests:tests.map(t=>({...t.source,base:numeric(t.base),elite:numeric(t.elite),...(modern?{parameters:t.source.parameters||{},max_points:numeric(t.max),scoring:t.scoring.value}:{})})),categories:cats.map(c=>({name:c.name.value.trim(),sex:c.sex.value,min:numeric(c.min),max:numeric(c.max)})),price_tiers:prices.map(p=>({name:p.name.value.trim(),amount:p.amount.value===''?null:Math.round(Number(p.amount.value)*100),start:iso(p.start),end:iso(p.end)})),discounts:discounts.map(d=>({code:d.code.value.trim().toUpperCase(),kind:d.kind.value,value:d.kind.value==='fixed'?(d.value.value===''?null:Math.round(Number(d.value.value)*100)):numeric(d.value),limit:numeric(d.limit),start:iso(d.start),end:iso(d.end)}))};q('#rules-input').value=JSON.stringify(data);q('#config-status').textContent='Guardando configuración…'});
 if(!modern){q('#add-test').disabled=true;q('#equal-points').disabled=true;toast('Edición con escala anterior: conserva sus reglas e historial. Los nuevos eventos usan parámetros por estación.')}
 if(form.dataset.locked==='1')qa('input,select,button,textarea',form).filter(n=>!n.matches('[data-event-step],#previous-step,#next-step')).forEach(n=>n.disabled=true);
}
