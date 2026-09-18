const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs');
function setup(value='',required=false){
 class E{constructor(){this.dataset={};this.children=[];this.listeners={};this.value='';this.placeholder='';this.disabled=false}append(...c){this.children.push(...c)}setAttribute(k,v){this[k]=v}addEventListener(k,f){this.listeners[k]=f}setCustomValidity(v){this.error=v}after(e){this.group=e}closest(){return {firstChild:{textContent:'Inicio'}}}dispatchEvent(){this.notified=true}}
 const input=new E();input.value=value;input.required=required;input.placeholder='dd/mm/aaaa HH:MM';input.form=new E();
 const context={document:{createElement:()=>new E(),querySelectorAll:()=>[input],body:{}},MutationObserver:class{observe(){}},Event:class{},setTimeout:f=>f()};
 vm.runInNewContext(fs.readFileSync('static/date-fields.js','utf8'),context);
 const [day,clock,clear]=input.group.children;const time=clock.children[0],picker=day.children[1].children[1];
 return {input,date:day.children[0],time,picker,clear,change:()=>time.listeners.change()};
}
test('display stays day-first and keeps local 24-hour time',()=>{
 const f=setup('18/09/2026 00:05',true);
 assert.equal(f.date.value,'18/09/2026');assert.equal(f.date.type,'text');assert.equal(f.time.value,'00:05');
 f.time.value='2330';f.time.listeners.input();assert.equal(f.time.value,'23:30');assert.equal(f.input.value,'18/09/2026 23:30');
 f.picker.value='2026-12-03';f.picker.listeners.change();assert.equal(f.date.value,'03/12/2026');assert.equal(f.input.value,'03/12/2026 23:30');
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
