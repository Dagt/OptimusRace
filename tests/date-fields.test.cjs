const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs');
function setup(value='',required=false){
 class E{constructor(){this.dataset={};this.children=[];this.listeners={};this.value='';this.placeholder='';this.disabled=false}append(...c){this.children.push(...c)}setAttribute(k,v){this[k]=v}addEventListener(k,f){this.listeners[k]=f}setCustomValidity(v){this.error=v}after(e){this.group=e}closest(){return {firstChild:{textContent:'Inicio'}}}dispatchEvent(e){this.notified=true;this.listeners[e.type]?.(e)}replaceChildren(...c){this.children=c}showModal(){this.open=true}close(){this.open=false}}
 const input=new E();input.value=value;input.required=required;input.placeholder='dd/mm/aaaa HH:MM';input.form=new E();
 const context={document:{createElement:()=>new E(),querySelectorAll:()=>[input],body:new E()},MutationObserver:class{observe(){}},Event:class{constructor(type){this.type=type}},setTimeout:f=>f()};
 vm.runInNewContext(fs.readFileSync('static/date-fields.js','utf8'),context);
 const [day,clock,clear]=input.group.children;const time=clock.children[0],dateButton=day.children[1],timeButton=clock.children[1];
 return {input,date:day.children[0],time,dateButton,timeButton,dialogs:context.document.body.children,clear,change:()=>time.listeners.change()};
}
test('display stays day-first and keeps local 24-hour time',()=>{
 const f=setup('18/09/2026 00:05',true);
 assert.equal(f.date.value,'18/09/2026');assert.equal(f.date.type,'text');assert.equal(f.time.value,'00:05');
 f.time.value='2330';f.time.listeners.input();assert.equal(f.time.value,'23:30');assert.equal(f.input.value,'18/09/2026 23:30');
 f.dateButton.onclick();const calendar=f.dialogs[0];assert.equal(calendar.open,true);calendar.children[2].children.find(b=>b.textContent==='19').onclick();assert.equal(f.date.value,'19/09/2026');assert.equal(f.input.value,'19/09/2026 23:30');assert.equal(calendar.open,false);
});
test('optional dates allow blank but partial entries require both fields',()=>{
 const f=setup();assert.equal(f.date.required,false);assert.equal(f.clear.hidden,true);
 f.date.value='18/09/2026';f.change();assert.equal(f.time.required,true);assert.equal(f.input.value,'');
 f.time.value='12:30';f.change();assert.equal(f.input.value,'18/09/2026 12:30');
 f.clear.onclick();assert.equal(f.date.required,false);assert.equal(f.input.value,'');
});
test('ISO dates initialize and form reset restores original values',()=>{
 const f=setup('2026-10-01T15:45');assert.equal(f.input.value,'01/10/2026 15:45');
 f.clear.onclick();f.input.form.listeners.reset();assert.equal(f.input.value,'01/10/2026 15:45');
});
test('invalid times and impossible dates block submission',()=>{
 const f=setup('18/09/2026 09:30');f.time.value='25:70';f.change();assert.ok(f.time.error);
 f.time.value='12:00';f.date.value='31/02/2026';f.change();assert.ok(f.date.error);
 const invalid=setup('invalid');assert.ok(invalid.date.error);assert.equal(invalid.input.value,'invalid');
});

test('hour can be selected as well as typed and both pickers reopen',()=>{
 const f=setup('18/09/2026 09:30');f.timeButton.onclick();
 const dialog=f.dialogs[1],fields=dialog.children[1];
 fields.children[0].children[0].value='17';fields.children[1].children[0].value='45';
 dialog.children[2].onclick();assert.equal(f.time.value,'17:45');assert.equal(f.input.value,'18/09/2026 17:45');assert.equal(dialog.open,false);
 f.timeButton.onclick();assert.equal(dialog.open,true);assert.equal(fields.children[0].children[0].value,'17');
 f.dateButton.onclick();f.dialogs[0].close();f.dateButton.onclick();assert.equal(f.dialogs[0].open,true);
});
