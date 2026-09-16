// State tests only: no browser, real camera, network or participant data.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

function fixture(){
  class Element {
    constructor(){this.hidden=false;this.disabled=false;this.innerHTML='';this.files=[];this.dataset={};this.listeners={}}
    addEventListener(type,fn){this.listeners[type]=fn}
    replaceChildren(...children){this.innerHTML=children.length?'portrait-preview':''}
    showModal(){this.open=true}
    close(){this.open=false;this.listeners.close?.()}
  }
  const elements=new Map(),get=selector=>{
    if(!elements.has(selector))elements.set(selector,new Element());
    return elements.get(selector);
  };
  const widget=new Element(),form=new Element();
  widget.dataset.portraitUrl='/preview/';
  get('input[name="photo"]').form=form;
  get('[name="csrfmiddlewaretoken"]').value='test';
  get('video').play=async()=>{};
  const state={calls:[],stopped:0};
  const track={stop(){state.stopped++}};
  const context={
    qa:s=>s==='[data-photo-widget]'?[widget]:[],q:s=>get(s),
    DataTransfer:class {constructor(){this.files=[];this.items={add:file=>this.files.push(file)}}},
    FormData:class {append(){}},AbortController,Image:Element,
    URL:{createObjectURL:()=>`blob:${state.calls.length}`,revokeObjectURL:()=>{}},
    fetch:()=>new Promise((resolve,reject)=>state.calls.push({resolve,reject})),
    navigator:{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[track]})}},
    document:new Element(),window:new Element()
  };
  vm.runInNewContext(fs.readFileSync('static/photo-editor.js','utf8'),context);
  const photo={name:'photo.jpg',type:'image/jpeg',size:100};
  async function upload(){get('input[name="photo"]').files=[photo];get('input[name="photo"]').listeners.change();await Promise.resolve()}
  async function complete(){state.calls.at(-1).resolve({ok:true,headers:{get:()=> 'image/jpeg'},blob:async()=>({})});await new Promise(resolve=>setImmediate(resolve))}
  return {get,widget,form,state,context,upload,complete,photo};
}

test('capture actions follow state; a preview must be accepted before saving',async()=>{
  const f=fixture();f.get('[data-photo-open]').onclick();
  assert.equal(f.widget.dataset.captureState,'choose');
  assert.equal(f.get('[data-photo-use]').hidden,true);
  await f.get('[data-camera-open]').onclick();
  assert.equal(f.widget.dataset.captureState,'camera');
  assert.equal(f.get('[data-photo-sources]').hidden,true);
  assert.equal(f.get('[data-camera-capture]').hidden,false);
  await f.upload();assert.equal(f.widget.dataset.captureState,'processing');
  let prevented=false;
  f.form.listeners.submit({preventDefault(){prevented=true},stopImmediatePropagation(){}});
  assert.equal(prevented,true);
  await f.complete();assert.equal(f.widget.dataset.captureState,'review');
  assert.equal(f.get('[data-camera-capture]').hidden,true);
  assert.equal(f.get('[data-photo-use]').hidden,false);
  f.get('[data-photo-use]').onclick();
  assert.equal(f.widget.dataset.captureState,'choose');
  assert.equal(f.get('[data-photo-dialog]').open,false);
  assert.equal(f.get('input[name="original_photo"]').files[0],f.photo);
});

test('cancelling a replacement preserves the accepted photo and stops camera',async()=>{
  const f=fixture();await f.upload();await f.complete();f.get('[data-photo-use]').onclick();
  f.get('[data-photo-open]').onclick();await f.get('[data-camera-open]').onclick();
  f.get('[data-photo-cancel]').onclick();
  assert.equal(f.state.stopped,1);
  assert.equal(f.get('input[name="photo"]').files[0],f.photo);
  assert.equal(f.get('[data-photo-preview]').innerHTML,'portrait-preview');
});

test('late camera rejection or preview response cannot reopen a cancelled capture',async()=>{
  const f=fixture();let reject;
  f.context.navigator.mediaDevices.getUserMedia=()=>new Promise((_,r)=>reject=r);
  const opening=f.get('[data-camera-open]').onclick();f.get('[data-photo-cancel]').onclick();
  reject(new Error('permission'));await opening;
  assert.equal(f.widget.dataset.captureState,'choose');
  await f.upload();f.get('[data-photo-cancel]').onclick();await f.complete();
  assert.equal(f.widget.dataset.captureState,'choose');
  assert.equal(f.get('input[name="photo"]').files.length,0);
});

test('processing errors allow retry but never accept an unprocessed image',async()=>{
  const f=fixture();await f.upload();f.state.calls[0].reject(new Error('offline'));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.widget.dataset.captureState,'error');
  assert.equal(f.get('[data-photo-use]').hidden,true);
  assert.equal(f.get('[data-photo-retry]').hidden,false);
  f.get('[data-photo-retry]').onclick();await f.complete();
  assert.equal(f.widget.dataset.captureState,'review');
});
