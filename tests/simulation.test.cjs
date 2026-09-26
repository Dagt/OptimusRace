const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('static/simulation.js','utf8');
function setup(){
 const calls=[];
 const window={fetch:(...args)=>{calls.push(args);return Promise.resolve({ok:true})}};
 vm.runInNewContext(source,{window,location:{href:'https://race.example/simulations/abc/events/1/coach/',origin:'https://race.example'},document:{currentScript:{dataset:{prefix:'/simulations/abc'}}},URL,Request});
 return {window,calls};
}
test('simulation fetch keeps hard-coded actions inside the copied event',async()=>{
 const {window,calls}=setup();const options={method:'POST',body:'value=25'};
 await window.fetch('/events/1/coach/',options);
 assert.equal(calls[0][0],'https://race.example/simulations/abc/events/1/coach/');
 assert.equal(calls[0][1],options);
});
test('simulation requests preserve already scoped URLs, media and external photos',async()=>{
 const {window,calls}=setup();
 for(const url of ['/simulations/abc/events/1/live/','/static/tv.js','https://photos.example/athlete.jpg'])await window.fetch(url);
 assert.equal(calls[0][0],'https://race.example/simulations/abc/events/1/live/');
 assert.equal(calls[1][0],'https://race.example/static/tv.js');
 assert.equal(calls[2][0],'https://photos.example/athlete.jpg');
});
