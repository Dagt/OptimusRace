const {test}=require('node:test'),assert=require('node:assert/strict');
const env={ORIGIN_URL:'https://origin.up.railway.app',WORKER_PROXY_SECRET:'test-secret'};
test('Worker relays cookies and CSRF, rewrites redirects and never caches',async()=>{
 const worker=(await import('../deploy/cloudflare/worker.mjs')).default,original=global.fetch;
 global.fetch=async(request,options)=>{
  assert.equal(request.url,'https://origin.up.railway.app/login/?next=%2F');
  assert.equal(request.headers.get('cookie'),'sessionid=test');
  assert.equal(request.headers.get('x-optimus-proxy-token'),'test-secret');
  assert.equal(request.headers.get('origin'),'https://race.workers.dev');
  assert.equal(request.headers.get('x-forwarded-host'),null);
  assert.equal(options.cache,'no-store');
  return new Response(null,{status:302,headers:{Location:'https://origin.up.railway.app/profile/','Set-Cookie':'sessionid=new; Secure; HttpOnly'}});
 };
 try{const response=await worker.fetch(new Request('https://race.workers.dev/login/?next=%2F',{headers:{Cookie:'sessionid=test',Origin:'https://race.workers.dev','X-Forwarded-Host':'attacker.test'}}),env);
 assert.equal(response.headers.get('location'),'https://race.workers.dev/profile/');
 assert.equal(response.headers.get('set-cookie'),'sessionid=new; Secure; HttpOnly');
 assert.equal(response.headers.get('cache-control'),'private, no-store');
 }finally{global.fetch=original}
});
test('Worker fails closed without configuration',async()=>{
 const worker=(await import('../deploy/cloudflare/worker.mjs')).default;
 assert.equal((await worker.fetch(new Request('https://race.workers.dev'),{})).status,503);
});

test('Worker preserves uploaded form bodies',async()=>{
 const worker=(await import('../deploy/cloudflare/worker.mjs')).default,original=global.fetch;
 const form=new FormData();form.set('csrfmiddlewaretoken','csrf');form.set('photo',new Blob(['photo-bytes'],{type:'image/jpeg'}),'photo.jpg');
 global.fetch=async(request)=>{
  assert.equal(request.method,'POST');
  const received=await request.formData();
  assert.equal(received.get('csrfmiddlewaretoken'),'csrf');
  assert.equal(await received.get('photo').text(),'photo-bytes');
  return new Response('saved');
 };
 try{assert.equal(await (await worker.fetch(new Request('https://race.workers.dev/profile/',{method:'POST',body:form}),env)).text(),'saved');}
 finally{global.fetch=original;}
});
