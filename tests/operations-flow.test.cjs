const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('static/operations.js','utf8');
function element(props={}){return Object.assign({listeners:{},addEventListener(type,fn){this.listeners[type]=fn}},props)}
test('station is disabled until a different selection; unchanged submit never prompts',()=>{
 const form=element({dataset:{current:'0'}}),select=element({value:'0'}),button={};let prompts=0;
 vm.runInNewContext(source,{qa:key=>key==='[data-station-switch]'?[form]:[],q:key=>key.startsWith('select')?select:button,confirm:()=>{prompts++;return true}});
 assert.equal(button.disabled,true);let prevented=false;
 form.listeners.submit({preventDefault(){prevented=true}});assert.equal(prevented,true);assert.equal(prompts,0);
 select.value='1';select.listeners.change();assert.equal(button.disabled,false);
 form.listeners.submit({preventDefault(){}});assert.equal(prompts,1);assert.equal(button.disabled,true);
 form.dataset.stale='1';select.listeners.change();assert.equal(button.disabled,true);
});
test('tie order prevents choosing the same athlete twice and releases changed choices',()=>{
 const form={},selects=[1,2].map(()=>element({value:'',options:['','1','2'].map(value=>({value}))}));
 vm.runInNewContext(source,{qa:key=>key==='[data-tie-form]'?[form]:key==='select[name="member"]'?selects:[]});
 selects[0].value='1';selects[0].listeners.change();assert.equal(selects[1].options[1].disabled,true);
 assert.equal(selects[0].options[1].disabled,false);
 selects[0].value='2';selects[0].listeners.change();assert.equal(selects[1].options[1].disabled,false);assert.equal(selects[1].options[2].disabled,true);
});
