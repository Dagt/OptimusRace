const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function setup(width=800,height=200,count=3){
 class Element{
  constructor(text=''){this.textContent=text;this.value='';this.children=[];this.style={};this.dataset={};this.clientHeight=height;this.clientWidth=width;this.classList={add(){}}}
  append(...items){this.children.push(...items)}
  replaceChildren(...items){this.children=items}
  addEventListener(){}
 }
 const map=new Map(),q=key=>{if(!map.has(key))map.set(key,new Element());return map.get(key)};
 q('#tv').dataset.source='/live/';
 const state={fail:false,feed:{phase:'open',test:'Salto',updated:'2026-09-16T10:00:00Z',relative_scoring:true,board:Array.from({length:count},(_,i)=>i+1).map(id=>({id,name:'Participante '+id,bib:id,category:id===3?'Femenil':'Varonil',completed:1,test_count:2,total:50,rank:id}))},timers:[],intervals:[]};
 const context={q,node:(tag,text,cls)=>{const e=new Element(text);e.className=cls;return e},fmt:String,dots:()=>new Element(),
  document:{body:new Element(),addEventListener(){}},window:{addEventListener(){}},getComputedStyle:()=>({getPropertyValue:()=>88}),
  jsonFetch:async()=>{if(state.fail)throw new Error('offline');return structuredClone(state.feed)},
  setTimeout:fn=>state.timers.push(fn),setInterval:(fn,ms)=>state.intervals.push({fn,ms}),toast(){}};
 vm.runInNewContext(fs.readFileSync('static/tv.js','utf8'),context);
 return {q,state,poll:()=>state.timers.at(-1)()};
}
test('TV page size uses available board height and rotates without dropping participants',async()=>{
 const f=setup();await flush();assert.equal(f.q('#tv-board').children.length,2);
 assert.match(f.q('#tv-page').textContent,/01 \/ 02/);
 f.state.intervals.find(x=>x.ms===10000).fn();assert.equal(f.q('#tv-board').children.length,1);
 assert.match(f.q('#tv-page').textContent,/02 \/ 02/);
 f.q('#tv-category').value='Femenil';f.q('#tv-category').onchange();assert.equal(f.q('#tv-board').children.length,1);
 assert.match(f.q('#tv-page').textContent,/01 \/ 01/);
});
test('TV distinguishes waiting, live provisional and final states',async()=>{
 const f=setup();await flush();assert.equal(f.q('#tv-status').textContent,'EN ESPERA DE INICIO');
 f.state.feed.phase='live';await f.poll();assert.equal(f.q('#tv-status').textContent,'PROVISIONALES · RELATIVOS');
 f.state.feed.phase='closed';await f.poll();assert.equal(f.q('#tv-status').textContent,'RESULTADOS FINALES');
});
test('connection failure retains the last received standings and recovers',async()=>{
 const f=setup();await flush();const rows=f.q('#tv-board').children;
 f.state.fail=true;await f.poll();assert.equal(f.q('#tv-status').textContent,'SIN CONEXIÓN');
 assert.equal(f.q('#tv-board').children,rows);
 f.state.fail=false;await f.poll();assert.equal(f.q('#tv-status').textContent,'EN ESPERA DE INICIO');
});


test('wide TV fills two columns and rotates through every athlete',async()=>{
 const f=setup(1800,800,40);await flush();
 assert.equal(f.q('#tv').dataset.columns,'2');
 assert.equal(f.q('#tv-board').children.length,16);
 assert.equal(f.q('#tv-board').style.gridTemplateColumns,'repeat(2, minmax(0,1fr))');
 f.state.intervals.find(x=>x.ms===10000).fn();assert.equal(f.q('#tv-board').children.length,16);
 f.state.intervals.find(x=>x.ms===10000).fn();assert.equal(f.q('#tv-board').children.length,8);
 assert.match(f.q('#tv-page').textContent,/03 \/ 03/);
});

test('tall display is not capped at twelve rows',async()=>{
 const f=setup(1000,1600,30);await flush();assert.equal(f.q('#tv-board').children.length,16);
});
