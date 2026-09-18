const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs');
function setup(value='',required=false){
 class E{constructor(){this.dataset={};this.children=[];this.listeners={};this.value='';this.placeholder='';this.disabled=false}append(...c){this.children.push(...c)}setAttribute(k,v){this[k]=v}addEventListener(k,f){this.listeners[k]=f}setCustomValidity(v){this.error=v}after(e){this.group=e}closest(){return {firstChild:{textContent:'Inicio'}}}dispatchEvent(){this.notified=true}}
 const input=new E();input.value=value;input.required=required;input.placeholder='dd/mm/aaaa HH:MM';input.form=new E();
 const context={document:{createElement:()=>new E(),querySelectorAll:()=>[input],body:{}},MutationObserver:class{observe(){}},Event:class{},setTimeout:f=>f()};
 vm.runInNewContext(fs.readFileSync('static/date-fields.js','utf8'),context);
 const [day,clock,clear]=input.group.children;const [hour,,minute]=clock.children;
 return {input,date:day.children[0],hour,minute,clear,change:()=>hour.listeners.change()};
}
test('stored day-first dates retain exact local hours without timezone conversion',()=>{
 const f=setup('18/09/2026 00:05',true);
 assert.equal(f.date.value,'2026-09-18');assert.equal(f.hour.value,'00');assert.equal(f.minute.value,'05');
 assert.equal(f.hour.children.length,25);assert.equal(f.minute.children.length,61);
 f.hour.value='23';f.change();assert.equal(f.input.value,'18/09/2026 23:05');
});
test('optional dates allow blank but partial entries require all parts',()=>{
 const f=setup();assert.equal(f.date.required,false);assert.equal(f.clear.hidden,true);
 f.date.value='2026-09-18';f.change();assert.equal(f.hour.required,true);assert.equal(f.minute.required,true);assert.equal(f.input.value,'');
 f.hour.value='12';f.minute.value='30';f.change();assert.equal(f.input.value,'18/09/2026 12:30');
 f.clear.onclick();assert.equal(f.date.required,false);assert.equal(f.input.value,'');
});
test('ISO dates initialize and form reset restores original values',()=>{
 const f=setup('2026-10-01T15:45');assert.equal(f.input.value,'01/10/2026 15:45');
 f.clear.onclick();f.input.form.listeners.reset();assert.equal(f.input.value,'01/10/2026 15:45');
});
test('invalid existing value cannot silently become an empty optional field',()=>{
 const f=setup('invalid');assert.ok(f.date.error);assert.equal(f.input.value,'invalid');
});
