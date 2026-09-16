/* Native event editor: all policy values travel through server validation. */
if(q('#config-form')){
 const form=q('#config-form'),original=JSON.parse(q('#initial-rules').textContent),catalog=JSON.parse(q('#catalog').textContent),modern=original.schema_version===2,caps=['Fuerza','Resistencia','Velocidad','Potencia'];
 function field(parent,label,value,type='text',options){const l=node('label',label),input=node(options?'select':'input');if(options)options.forEach(([v,t])=>{const o=node('option',t);o.value=v;input.append(o)});else{input.type=type==='datetime-local'?'text':type;if(type==='datetime-local'){input.placeholder='dd/mm/aaaa HH:MM';input.pattern='[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}';input.addEventListener('input',()=>{const m=input.value.match(/^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/),date=m?new Date(Date.UTC(+m[3],+m[2]-1,+m[1])):null,valid=!input.value||(m&&date.getUTCFullYear()===+m[3]&&date.getUTCMonth()===+m[2]-1&&date.getUTCDate()===+m[1]&&+m[4]<24&&+m[5]<60);input.setCustomValidity(valid?'':'Escribe una fecha válida: dd/mm/aaaa HH:MM.')})}if(type==='number'){input.step='any';input.min=0}}input.value=value??'';l.append(input);parent.append(l);return input}
 const numeric=input=>input.value===''?null:Number(input.value);
 function removeButton(parent,remove){const b=node('button','Quitar','text-button');b.type='button';b.onclick=remove;parent.append(b)}
 const tests=[];let cats=[],prices=[],discounts=[];
 const auto=q('#auto-points');auto.checked=modern&&!(original.tests||[]).length;
 function distribute(){if(!tests.length)return;let used=0;tests.forEach((t,i)=>{const points=i===tests.length-1?100-used:Math.floor(1000000/tests.length)/10000;t.max.value=Number(points.toFixed(4));used+=points})}
 auto.onchange=()=>check();

 function check(){if(auto.checked)distribute();tests.forEach((t,i)=>{t.max.readOnly=auto.checked;t.index.textContent=String(i+1).padStart(2,'0');t.up.disabled=i===0;t.down.disabled=i===tests.length-1;if(t.refreshScore)t.refreshScore()});q('#capacity-check').replaceChildren(node('span',`${tests.length} estaciones · ${fmt(tests.reduce((n,t)=>n+(numeric(t.max)||0),0))} / 100 puntos`),...caps.map(c=>node('span',`${c}: ${tests.filter(t=>t.source.capacity===c).length}`)))}
 function addTest(t={}){
  const row=node('section',undefined,'config-test station-row'),body=node('div',undefined,'config-test-body'),grid=node('div',undefined,'station-fields'),index=node('span','','station-index');body.append(index,grid);row.append(body);q('#test-editor').append(row);
  const choice=field(grid,'Prueba del catálogo','','text',[['',t.name?'Conservar prueba guardada':'Selecciona una prueba'],...catalog.map((c,i)=>[String(i),c.name])]);choice.required=!t.name;
  const scoring=field(grid,'Cómo asignar puntos',t.scoring||(!modern?'linear':'relative'),'text',[['relative','Según mejor y peor de la categoría'],['judge','Puntos capturados por el juez'],['linear','Referencias fijas']]);
  const max=field(grid,'Puntos de esta prueba',t.max_points??1,'number');max.min='.01';
  const references=node('div',undefined,'station-references');body.append(references);
  const referenceHelp=node('p','Marcas objetivo definidas por el organizador. No son porcentajes del peso corporal.');references.append(referenceHelp);
  const referenceGrid=node('div',undefined,'form-grid');references.append(referenceGrid);
  const base=field(referenceGrid,'Marca que obtiene la mitad de los puntos',t.base,'number'),elite=field(referenceGrid,'Marca que obtiene todos los puntos',t.elite,'number');
  const description=node('p',undefined,'measurement-summary');body.append(description);
  const item={row,index,choice,scoring,max,base,elite,source:{...t}};tests.push(item);
  function summarize(){const c=item.source,p=c.parameters||{};row.setAttribute('aria-label',c.name||'Nueva estación');base.setAttribute('aria-label',`Marca para la mitad de los puntos (${c.unit||'unidad de la prueba'})`);elite.setAttribute('aria-label',`Marca para todos los puntos (${c.unit||'unidad de la prueba'})`);description.textContent=c.name?[c.capacity,`El juez registra ${c.unit}`,c.higher?'Mayor marca es mejor':'Menor marca es mejor',p.duration_seconds?`${p.duration_seconds} s de esfuerzo`:'',p.distance_meters?`${p.distance_meters} m × ${p.laps||1} recorridos`:'',p.load_mode==='body_percent'?`Carga: ${p.load_value}% corporal`:p.load_mode==='fixed'?`Carga: ${p.load_value} kg`:'',p.instructions||''].filter(Boolean).join(' · '):'Crea primero el ejercicio en el catálogo. Aquí no tienes que volver a definirlo.'}
  function scoreFields(){references.hidden=scoring.value!=='linear';base.disabled=elite.disabled=references.hidden;base.required=elite.required=!references.hidden;referenceHelp.textContent=`Marcas objetivo en ${item.source.unit||'la unidad de la prueba'}. Con ${max.value} puntos por estación: la primera marca otorga ${fmt(Number(max.value)/2)} y la segunda ${max.value}. No son porcentajes del peso corporal.`}scoring.onchange=scoreFields;item.refreshScore=scoreFields;
  choice.onchange=()=>{if(choice.value===''){item.source={...t};choice.required=!t.name}else{item.source=structuredClone(catalog[Number(choice.value)]);choice.required=false;item.source.max_points=numeric(max)}base.value=item.source.base??'';elite.value=item.source.elite??'';summarize();scoreFields();check()};
  max.oninput=()=>{auto.checked=false;check();scoreFields()};
  const actions=node('div',undefined,'station-actions');body.append(actions);
  for(const [label,delta] of [['Subir',-1],['Bajar',1]]){const button=node('button',label,'text-button');button.type='button';button.onclick=()=>{const i=tests.indexOf(item),j=i+delta;if(j<0||j>=tests.length)return;[tests[i],tests[j]]=[tests[j],tests[i]];tests.forEach(entry=>q('#test-editor').append(entry.row));check()};button.setAttribute('aria-label',`${label} estación`);item[delta===-1?'up':'down']=button;actions.append(button)}
  removeButton(actions,()=>{tests.splice(tests.indexOf(item),1);row.remove();check()});summarize();scoreFields();check();
 }
 (original.tests||[]).forEach(addTest);q('#add-test').onclick=()=>addTest();q('#equal-points').onclick=()=>{distribute();check()};check();
 const branches={};
 const categoryName=c=>`${c.sex.value==='M'?'Varonil':'Femenil'} · ${c.min.value||'0'}${c.max.value===''?' kg en adelante':`–${c.max.value} kg`}`;
 for(const [sex,label] of [['M','Varonil'],['F','Femenil']]){
  const group=node('section',undefined,'category-branch'),list=node('div'),tools=node('div',undefined,'category-tools');
  group.append(node('h3',label),list,tools);q('#category-editor').append(group);branches[sex]=list;
  const add=node('button',`Agregar categoría ${label.toLowerCase()}`,'button secondary small');add.type='button';tools.append(add);
  add.onclick=()=>{const existing=cats.filter(c=>c.sex.value===sex),last=existing.at(-1);addCat({sex,min:last&&last.max.value!==''?numeric(last.max):0});q('#config-status').textContent='Tienes cambios sin guardar.'};
  const bulk=node('div',undefined,'category-bulk'),bounds=field(bulk,'Crear varios rangos · límites en kg','');bounds.placeholder='Ejemplo: 60, 70, 80, 90';
  const generate=node('button','Agregar rangos','button secondary small');generate.type='button';bulk.append(generate);tools.append(bulk);
  const feedback=node('p','','inline-error');feedback.setAttribute('role','alert');tools.append(feedback);
  generate.onclick=()=>{
   const raw=bounds.value.split(',').map(x=>x.trim()),values=raw.map(Number);feedback.textContent='';
   if(raw.some(x=>!x)||values.length<2||values.some((v,i)=>!Number.isFinite(v)||v<0||(i&&v<=values[i-1]))){feedback.textContent='Escribe al menos dos límites crecientes, separados por coma. Usa punto para decimales.';return}
   const ranges=values.slice(0,-1).map((min,i)=>({sex,min,max:values[i+1]}));
   if(cats.some(c=>c.sex.value===sex&&ranges.some(r=>r.min<(numeric(c.max)??Infinity)&&r.max>numeric(c.min)))){feedback.textContent='Los rangos se cruzan con categorías existentes. Revisa sus límites antes de agregarlos.';return}
   ranges.forEach(addCat);bounds.value='';q('#config-status').textContent='Tienes cambios sin guardar.';
  };
 }
 function addCat(c={}){
  const sex={value:c.sex||'M'},row=node('div',undefined,'category-weight-row');branches[sex.value].append(row);
  const min=field(row,'Desde · kg',c.min??0,'number'),max=field(row,original.category_bounds==='upper_inclusive'?'Hasta · kg (incluido)':'Hasta · kg (excluido)',c.max,'number');max.placeholder='Sin límite';
  const preview=node('small','','category-preview');row.append(preview);const item={sex,min,max,originalName:c.name,changed:!c.name};cats.push(item);
  const update=()=>{item.changed=true;preview.textContent=categoryName(item)};min.oninput=max.oninput=update;preview.textContent=c.name||categoryName(item);
  removeButton(row,()=>{cats=cats.filter(i=>i!==item);row.remove();q('#config-status').textContent='Tienes cambios sin guardar.'});
 }
 (original.categories||[]).forEach(addCat);
 // datetime-local is expressed in the venue's configured Mexico City timezone, not the browser's zone.
 function local(value){if(!value)return '';if(!Number.isFinite(new Date(value).getTime()))return value;const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(value));const p=Object.fromEntries(parts.map(item=>[item.type,item.value]));return `${p.day}/${p.month}/${p.year} ${p.hour}:${p.minute}`}
 function iso(input){if(!input.value)return null;const match=input.value.match(/^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/);return match?`${match[3]}-${match[2]}-${match[1]}T${match[4]}:${match[5]}:00-06:00`:input.value}
 function addPrice(p={}){const row=node('div',undefined,'policy-row price-policy-row');q('#price-editor').append(row);const name=field(row,'Nombre de tarifa',p.name),amount=field(row,'Importe · MXN',p.amount==null?'':p.amount/100,'number'),start=field(row,'Desde (incluido)',local(p.start),'datetime-local'),end=field(row,'Hasta (excluido)',local(p.end),'datetime-local');amount.step='.01';const item={name,amount,start,end};prices.push(item);removeButton(row,()=>{prices=prices.filter(i=>i!==item);row.remove()})}
 (original.price_tiers||[]).forEach(addPrice);q('#add-price').onclick=()=>addPrice();
 function addDiscount(d={}){const row=node('div',undefined,'policy-row discount-policy-row');q('#discount-editor').append(row);const code=field(row,'Código',d.code),kind=field(row,'Tipo',d.kind||'percent','text',[['percent','Porcentaje'],['fixed','Importe fijo · MXN']]),value=field(row,'Descuento · % o MXN',d.kind==='fixed'?d.value/100:d.value,'number'),limit=field(row,'Límite de usos',d.limit,'number'),start=field(row,'Desde (opcional)',local(d.start),'datetime-local'),end=field(row,'Hasta (opcional)',local(d.end),'datetime-local');value.step='.01';limit.step='1';limit.placeholder='Sin límite';
 const updateDiscountUnit=()=>{value.parentElement.firstChild.textContent=kind.value==='percent'?'Descuento · %':'Descuento · MXN';value.max=kind.value==='percent'?'100':''};kind.onchange=updateDiscountUnit;updateDiscountUnit();const item={code,kind,value,limit,start,end};discounts.push(item);removeButton(row,()=>{discounts=discounts.filter(i=>i!==item);row.remove()})}
 (original.discounts||[]).forEach(addDiscount);q('#add-discount').onclick=()=>addDiscount();
 form.addEventListener('input',()=>q('#config-status').textContent='Tienes cambios sin guardar.');
 form.addEventListener('submit',event=>{if(event.submitter?.value==='publish'&&!confirm('Publicar hará visible el evento y fijará sus reglas. ¿Guardar y publicar?')){event.preventDefault();return}const data={...original,tests:tests.map(t=>({...t.source,base:numeric(t.base),elite:numeric(t.elite),...(modern?{parameters:t.source.parameters||{},max_points:numeric(t.max),scoring:t.scoring.value}:{})})),categories:cats.map(c=>({name:c.changed?categoryName(c):c.originalName,sex:c.sex.value,min:numeric(c.min),max:numeric(c.max)})),price_tiers:prices.map(p=>({name:p.name.value.trim(),amount:p.amount.value===''?null:Math.round(Number(p.amount.value)*100),start:iso(p.start),end:iso(p.end)})),discounts:discounts.map(d=>({code:d.code.value.trim().toUpperCase(),kind:d.kind.value,value:d.kind.value==='fixed'?(d.value.value===''?null:Math.round(Number(d.value.value)*100)):numeric(d.value),limit:numeric(d.limit),start:iso(d.start),end:iso(d.end)}))};q('#rules-input').value=JSON.stringify(data);q('#config-status').textContent='Guardando configuración…'});
 if(!modern){q('#add-test').disabled=true;q('#equal-points').disabled=true;toast('Edición con escala anterior: conserva sus reglas e historial. Los nuevos eventos usan parámetros por estación.')}
 if(form.dataset.locked==='1')qa('input,select,button,textarea',form).filter(n=>!n.matches('[data-event-step],#previous-step,#next-step')).forEach(n=>n.disabled=true);
}
