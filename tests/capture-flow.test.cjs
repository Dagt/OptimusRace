const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));

function setup(count=1,restoredValue=null){
 class Element{
  constructor(){this.value='';this.dataset={};this.hidden=false;this.disabled=false;this.style={};this.listeners={};this.classList={add(){},toggle(){}}}
  prepend(child){this.prepended=child}
  addEventListener(type,fn){this.listeners[type]=fn}
  setAttribute(k,v){(this.attributes??={})[k]=v} getAttribute(k){return this.attributes?.[k]} removeAttribute(){} focus(){this.focused=true}
  replaceChildren(...children){this.children=children;this.textContent=children.map(c=>c.textContent||'').join('')}
 }
 const globals=new Map(),locals=new Map(),form=new Element();
 const element=(map,key)=>{if(!map.has(key))map.set(key,new Element());return map.get(key)};
 const localMaps=new Map([[form,locals]]);
 const q=(key,root)=>element(localMaps.get(root)||globals,key);
 form.elements={};for(const [key,value] of Object.entries({registration:'1',test:'0',revision:'0',value:'',status:'done',reason:''})){form.elements[key]=new Element();form.elements[key].value=value}
 form.dataset={enabled:'1',done:'0',status:'pending',attendance:'pending',bib:'1',search:'Ana 1'};
 const forms=[form];for(let i=2;i<=count;i++){const f=new Element();f.dataset={...form.dataset,bib:String(i),search:'Atleta '+i};f.elements={};for(const [k,v] of Object.entries(form.elements)){f.elements[k]=new Element();f.elements[k].value=k==='registration'?String(i):v.value}forms.push(f);localMaps.set(f,new Map())}
 forms.forEach(f=>{const defaults=Object.fromEntries(Object.entries(f.elements).map(([k,v])=>[k,v.value]));f.reset=()=>{for(const [k,v] of Object.entries(defaults))f.elements[k].value=v}});
 if(restoredValue!==null)form.elements.value.value=restoredValue;
 const filters=['all','pending','done','drafts','search'].map(filter=>{const b=new Element();b.dataset.filter=filter;return b});
 const list=q('#capture-list');list.dataset={liveUrl:'/live/',test:'0'};
 q('#capture-test').textContent=JSON.stringify({scoring:'relative',max_points:100});
 const mark={revision:0,value:null,load:null,points:null,status:'pending'};
 const state={feed:{phase:'live',test_index:0,board:forms.map((f,i)=>({id:i+1,attendance:'present',marks:[i?{...mark}:mark]}))},posts:[],intervals:[]};
 const context={q,toast:text=>{state.toast=text},qa:(key,root)=>key==='.capture-card'?forms:root===q('#coach-filter')?filters:[],
  node:(tag,text)=>({textContent:text}),fmt:String,stateNames:{pending:'Faltante',done:'Realizada',absent:'Ausente'},
  document:Object.assign(new Element(),{hidden:false,createElement:()=>new Element(),createTextNode:text=>({textContent:text})}),
  window:new Element(),navigator:{onLine:true},location:{pathname:'/coach/',replace:url=>{state.navigation=url}},confirm:()=>true,
  FormData:class{constructor(f){this.values=Object.fromEntries(Object.entries(f.elements).filter(([k,v])=>!v.disabled).map(([k,v])=>[k,v.value]))}get(key){return this.values[key]}},
  jsonFetch:async(url,options)=>options?.method==='POST'?await new Promise((resolve,reject)=>state.posts.push({resolve,reject,body:options.body})):structuredClone(state.feed),
  setInterval:fn=>state.intervals.push(fn)};
 vm.runInNewContext(fs.readFileSync('static/capture.js','utf8'),context);
 return {q,form,forms,filters,state,context,mark,poll:()=>state.intervals[0](),edit(value){form.elements.value.value=value;form.listeners.input()}};
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
 f.q('#coach-search').value='#001';f.q('#coach-search').oninput();f.q('#capture-options').children[0].onclick();assert.equal(f.form.hidden,false);
});


test('review queue has no pagination and preserves drafts when selecting another athlete',async()=>{
 const f=setup(20);await flush();f.filters[1].onclick();
 assert.equal(f.q('#capture-options').children.length,20);assert.ok(f.forms.every(x=>x.hidden));
 f.q('#capture-options').children[0].onclick();assert.equal(f.forms.filter(x=>!x.hidden).length,1);
 f.edit('55');f.q('#capture-next-pending').onclick();
 assert.equal(f.forms[1].hidden,false);assert.equal(f.form.hidden,true);
 assert.equal(f.form.elements.value.value,'55');assert.equal(f.q('#draft-count').textContent,1);
 f.filters[3].onclick();assert.equal(f.q('#capture-options').children.length,1);
 f.q('#capture-options').children[0].onclick();assert.equal(f.form.elements.value.value,'55');
 f.q('#coach-search').value='unmatched';f.q('#coach-search').oninput();
 assert.equal(f.q('#capture-options').children.length,0);assert.equal(f.form.hidden,false);
});

test('remote save updates selector and filters without changing the selected athlete',async()=>{
 const f=setup(8);await flush();f.filters[1].onclick();f.q('#capture-options').children[0].onclick();
 Object.assign(f.mark,{revision:1,value:42,points:100,status:'done'});await f.poll();
 assert.equal(f.q('#capture-options').children[0].dataset.registration,'2');
 f.filters[1].onclick();assert.equal(f.q('#capture-options').children[0].dataset.registration,'2');
 assert.equal(f.form.hidden,false);assert.equal(f.form.elements.value.value,42);
 f.filters[2].onclick();assert.equal(f.q('#capture-options').children.length,1);
 assert.equal(f.q('#capture-options').children[0].dataset.registration,'1');
});

test('absence is resolved for this station, without claiming event attendance',async()=>{
 const f=setup(2);await flush();f.filters[1].onclick();Object.assign(f.mark,{revision:1,status:'absent'});await f.poll();
 assert.equal(f.q('#pending-count').textContent,1);assert.equal(f.q('#capture-options').children[0].dataset.registration,'2');
 assert.equal(f.q('#capture-complete').textContent,1);
});
test('administrator closing a station blocks coach saves and preserves drafts',async()=>{
 const f=setup();await flush();f.edit('45');f.state.feed.station_closed=true;await f.poll();
 assert.equal(f.q('[data-save-mark]',f.form).disabled,true);assert.equal(f.form.elements.value.value,'45');
 await f.form.listeners.submit({preventDefault(){}});assert.equal(f.state.posts.length,0);
});

test('search starts empty, finds exact number and selects with Enter without saving',async()=>{
 const f=setup(20);await flush();
 assert.equal(f.q('#capture-options').children?.length||0,0);
 assert.equal(f.q('#capture-picker').hidden,true);assert.equal(f.q('#capture-empty').hidden,true);
 f.q('#coach-search').value='#001';f.q('#coach-search').oninput();
 assert.equal(f.q('#capture-options').children.length,1);
 f.q('#coach-search').onkeydown({key:'Enter',preventDefault(){}});
 assert.equal(f.form.hidden,false);assert.equal(f.q('#capture-picker').hidden,true);
 assert.equal(f.form.elements.value.focused,true);assert.equal(f.state.posts.length,0);
 f.edit('51');f.q('#capture-change').onclick();
 assert.equal(f.form.hidden,true);assert.equal(f.form.elements.value.value,'51');
 f.filters[3].onclick();f.q('#capture-options').children[0].onclick();
 assert.equal(f.form.elements.value.value,'51');
});
test('ambiguous search does not select a competitor on Enter',async()=>{
 const f=setup(20);await flush();f.q('#coach-search').value='Atleta';f.q('#coach-search').oninput();
 f.q('#coach-search').onkeydown({key:'Enter',preventDefault(){}});
 assert.ok(f.forms.every(x=>x.hidden));assert.equal(f.state.posts.length,0);
});

test('confirmed save closes selected card and leaves a visible confirmation',async()=>{
 const f=setup(2);await flush();f.filters[0].onclick();f.q('#capture-options').children[0].onclick();f.edit('45');
 const save=f.form.listeners.submit({preventDefault(){}});
 assert.equal(f.form.hidden,false);
 f.state.posts[0].resolve({revision:1,status:'done',points:100});await save;
 assert.ok(f.forms.every(x=>x.hidden));assert.ok(f.state.toast);
 assert.match(f.state.toast,/#001/);
});
test('failed save keeps selected card and its input visible',async()=>{
 const f=setup();await flush();f.filters[0].onclick();f.q('#capture-options').children[0].onclick();f.edit('45');
 const save=f.form.listeners.submit({preventDefault(){}});
 f.state.posts[0].reject(new Error('Failed to fetch'));await save;
 assert.equal(f.form.hidden,false);assert.equal(f.form.elements.value.value,'45');
});
test('late save confirmation does not close another competitor selected meanwhile',async()=>{
 const f=setup(2);await flush();f.filters[0].onclick();f.q('#capture-options').children[0].onclick();f.edit('45');
 const save=f.form.listeners.submit({preventDefault(){}});
 f.q('#capture-options').children[1].onclick();
 f.state.posts[0].resolve({revision:1,status:'done',points:100});await save;
 assert.equal(f.forms[1].hidden,false);assert.equal(f.form.hidden,true);
});

test('reload discards browser-restored values from a previous station',async()=>{
 const f=setup(1,'99');await flush();assert.equal(f.form.elements.value.value,'');
 f.form.elements.value.value='99';f.context.window.listeners.pageshow({persisted:false});await flush();
 assert.equal(f.form.elements.value.value,'');assert.equal(f.form.elements.revision.value,0);
});
test('closed station keeps polling and loads the next station automatically when clean',async()=>{
 const f=setup();await flush();f.state.feed.station_closed=true;await f.poll();
 assert.equal(f.q('[data-save-mark]',f.form).disabled,true);
 f.state.feed.station_closed=false;f.state.feed.test_index=1;await f.poll();
 assert.equal(f.state.navigation,'/coach/?station=1');
});
test('reopening the same station unlocks it without losing drafts',async()=>{
 const f=setup();await flush();f.edit('45');f.state.feed.station_closed=true;await f.poll();
 f.state.feed.station_closed=false;await f.poll();
 assert.equal(f.form.elements.value.value,'45');assert.equal(f.q('[data-save-mark]',f.form).disabled,false);
});
test('changing stations never reloads a coach with unsaved input',async()=>{
 const f=setup();await flush();f.edit('45');f.state.feed.test_index=1;await f.poll();await f.poll();
 assert.equal(f.state.navigation,undefined);assert.equal(f.form.elements.value.value,'45');
 assert.equal(f.q('[data-save-mark]',f.form).disabled,true);
});

test('changing tabs clears the selected card and search but preserves a recoverable draft',async()=>{
 const f=setup(3);await flush();f.filters[1].onclick();f.q('#capture-options').children[0].onclick();f.edit('55');
 f.filters[4].onclick();
 assert.ok(f.forms.every(x=>x.hidden));assert.equal(f.q('#capture-picker').hidden,true);
 assert.equal(f.q('#coach-search').value,'');assert.equal(f.q('#capture-change').hidden,true);
 assert.equal(f.form.elements.value.value,'55');
 await f.poll();assert.ok(f.forms.every(x=>x.hidden));
 f.filters[3].onclick();f.q('#capture-options').children[0].onclick();assert.equal(f.form.elements.value.value,'55');
 f.filters[0].onclick();assert.ok(f.forms.every(x=>x.hidden));
 assert.equal(f.q('#capture-options').children.length,3);
});

test('list selection exposes detail layout and return keeps the current tab',async()=>{
 const f=setup(3);await flush();f.filters[1].onclick();f.q('#capture-options').children[0].onclick();
 assert.equal(f.q('#capture-console').dataset.selected,'1');assert.equal(f.q('#capture-console').dataset.view,'pending');
 assert.equal(f.q('#capture-change').textContent,'Volver a lista');
 f.q('#capture-change').onclick();assert.ok(f.forms.every(x=>x.hidden));
 assert.equal(f.q('#capture-console').dataset.selected,'0');assert.equal(f.q('#capture-console').dataset.view,'pending');
 assert.equal(f.q('#capture-options').children.length,3);
});

test('calculated load is prefilled and polling preserves drafts and saved loads',async()=>{
 const f=setup();await flush();f.form.elements.load={value:'',disabled:false};f.form.dataset.suggestedLoad='56.775';
 await f.poll();assert.equal(f.form.elements.load.value,'56.775');
 f.form.elements.load.value='57.5';f.edit('15');await f.poll();assert.equal(f.form.elements.load.value,'57.5');
 Object.assign(f.mark,{revision:1,status:'done',value:15,load:60});await f.poll();
 f.q('[data-load-saved]',f.form).onclick();assert.equal(f.form.elements.load.value,60);
 await f.poll();assert.equal(f.form.elements.load.value,60);
});

test('every tab uses the same detail-only screen with next action inside the card',async()=>{
 const f=setup(3);await flush();
 for(const tab of [0,1]){
  f.filters[tab].onclick();f.q('#capture-options').children[0].onclick();
  assert.equal(f.q('#capture-picker').hidden,true);
  assert.equal(f.q('.capture-actions',f.form).prepended,f.q('#capture-list-actions'));
  assert.equal(f.q('#capture-list-actions').hidden,tab===1);
  f.q('#capture-change').onclick();assert.equal(f.q('#capture-picker').hidden,false);
  assert.equal(f.q('#capture-list-actions').hidden,true);
 }
});

test('pending tab hides next action while other tabs retain it',async()=>{
 const f=setup(2);await flush();f.filters[1].onclick();f.q('#capture-options').children[0].onclick();
 assert.equal(f.q('#capture-list-actions').hidden,true);
 f.filters[0].onclick();f.q('#capture-options').children[0].onclick();
 assert.equal(f.q('#capture-list-actions').hidden,false);
});

test('time format controls keep server seconds when saving and reloading',async()=>{
 const f=setup();await flush();
 f.form.elements.time_format={value:'minutes',disabled:false};
 f.edit('5.365');
 assert.equal(f.q('[data-mark-unit]',f.form).textContent,'min');
 const save=f.form.listeners.submit({preventDefault(){}});
 assert.equal(f.state.posts[0].body.get('time_format'),'minutes');
 assert.equal(f.form.elements.time_format.disabled,true);
 f.state.posts[0].resolve({revision:1,status:'done',points:100,value:321.9});
 await save;
 assert.equal(f.form.elements.value.value,321.9);
 assert.equal(f.form.elements.time_format.value,'seconds');
 f.form.elements.time_format.value='minutes_seconds';f.edit('5:36.5');
 assert.equal(f.form.elements.value.type,'text');
 assert.equal(f.q('[data-mark-unit]',f.form).textContent,'min:seg');
});
