const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));

function setup(){
 class Element{
  constructor(){this.value='';this.dataset={};this.hidden=false;this.disabled=false;this.style={};this.listeners={};this.classList={add(){},toggle(){}}}
  addEventListener(type,fn){this.listeners[type]=fn}
  setAttribute(){} removeAttribute(){} focus(){this.focused=true}
  replaceChildren(...children){this.textContent=children.map(c=>c.textContent||'').join('')}
 }
 const globals=new Map(),locals=new Map(),form=new Element();
 const element=(map,key)=>{if(!map.has(key))map.set(key,new Element());return map.get(key)};
 const q=(key,root)=>element(root===form?locals:globals,key);
 form.elements={};for(const [key,value] of Object.entries({registration:'1',test:'0',revision:'0',value:'',status:'done',reason:''})){form.elements[key]=new Element();form.elements[key].value=value}
 form.dataset={enabled:'1',done:'0',bib:'1',search:'Ana 1'};
 const list=q('#capture-list');list.dataset={liveUrl:'/live/',test:'0'};
 q('#capture-test').textContent=JSON.stringify({scoring:'relative',max_points:100});
 const mark={revision:0,value:null,load:null,points:null,status:'pending'};
 const state={feed:{phase:'live',test_index:0,board:[{id:1,attendance:'present',marks:[mark]}]},posts:[],intervals:[]};
 const context={q,qa:(key,root)=>key==='.capture-card'?[form]:[],
  node:(tag,text)=>({textContent:text}),fmt:String,stateNames:{pending:'Faltante',done:'Realizada',absent:'Ausente'},
  document:Object.assign(new Element(),{hidden:false,createTextNode:text=>({textContent:text})}),
  window:new Element(),navigator:{onLine:true},location:{pathname:'/coach/'},confirm:()=>true,
  FormData:class{constructor(f){this.values=Object.fromEntries(Object.entries(f.elements).filter(([k,v])=>!v.disabled).map(([k,v])=>[k,v.value]))}get(key){return this.values[key]}},
  jsonFetch:async(url,options)=>options?.method==='POST'?await new Promise((resolve,reject)=>state.posts.push({resolve,reject,body:options.body})):structuredClone(state.feed),
  setInterval:fn=>state.intervals.push(fn)};
 vm.runInNewContext(fs.readFileSync('static/capture.js','utf8'),context);
 return {q,form,state,context,mark,poll:()=>state.intervals[0](),edit(value){form.elements.value.value=value;form.listeners.input()}};
}

test('clean card receives another coach’s save and current relative points',async()=>{
 const f=setup();await flush();Object.assign(f.mark,{revision:1,value:42,points:100,status:'done'});await f.poll();
 assert.equal(f.form.elements.value.value,42);assert.equal(f.form.elements.revision.value,1);
 assert.equal(f.form.dataset.done,'1');assert.equal(f.q('.correction-reason',f.form).hidden,false);
 f.mark.points=0;await f.poll();assert.match(f.q('.capture-state',f.form).textContent,/0 pts/);
});

test('remote conflict preserves unsaved input and requires explicit server reload',async()=>{
 const f=setup();await flush();f.edit('45');Object.assign(f.mark,{revision:1,value:42,points:100,status:'done'});await f.poll();
 assert.equal(f.form.elements.value.value,'45');assert.equal(f.q('[data-save-mark]',f.form).disabled,true);
 assert.equal(f.q('[data-load-saved]',f.form).hidden,false);
 f.q('[data-load-saved]',f.form).onclick();assert.equal(f.form.elements.value.value,42);
 assert.equal(f.q('[data-save-mark]',f.form).disabled,false);
});

test('saving freezes fields, ignores double submission and sends enabled values',async()=>{
 const f=setup();await flush();f.edit('45');
 const save=f.form.listeners.submit({preventDefault(){}});
 assert.equal(f.form.elements.value.disabled,true);assert.equal(f.form.elements.status.disabled,true);
 await f.form.listeners.submit({preventDefault(){}});assert.equal(f.state.posts.length,1);
 assert.equal(f.state.posts[0].body.get('value'),'45');
 f.state.posts[0].resolve({revision:1,status:'done',points:100,provisional:true});await save;await flush();
 // An older in-flight poll must not roll the successful save back to revision zero.
 assert.equal(f.form.elements.revision.value,1);assert.equal(f.form.elements.value.value,'45');
 assert.equal(f.form.elements.value.disabled,false);
});

test('station change blocks submission while preserving the pending mark',async()=>{
 const f=setup();await flush();f.edit('45');f.state.feed.test_index=1;await f.poll();
 assert.equal(f.q('#stale-stage').hidden,false);assert.equal(f.form.elements.value.value,'45');
 assert.equal(f.q('[data-save-mark]',f.form).disabled,true);
 await f.form.listeners.submit({preventDefault(){}});assert.equal(f.state.posts.length,0);
});

test('unconfirmed network response preserves input; reconciliation exposes saved version',async()=>{
 const f=setup();await flush();f.edit('45');const save=f.form.listeners.submit({preventDefault(){}});
 Object.assign(f.mark,{revision:1,value:45,points:100,status:'done'});
 f.state.posts[0].reject(new Error('Failed to fetch'));await save;await flush();
 assert.equal(f.form.elements.value.value,'45');assert.equal(f.form.dataset.conflict,'1');
 assert.equal(f.q('[data-load-saved]',f.form).hidden,false);
});

test('new registration prompts roster refresh without blocking current captures',async()=>{
 const f=setup();await flush();f.state.feed.board.push({id:2,attendance:'present',marks:[]});await f.poll();
 assert.equal(f.q('#roster-changed').hidden,false);assert.equal(f.q('[data-save-mark]',f.form).disabled,false);
 f.q('#coach-search').value='#001';f.q('#coach-search').oninput();assert.equal(f.form.hidden,false);
});
