const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');const A=require('./four_pass_sparse.js');let tests=0;
async function worker(file){const msgs=[];const self={postMessage:x=>msgs.push(x)};const sandbox={self,importScripts:()=>{},EdgeLabFourPass:A,TextDecoderStream};vm.runInNewContext(fs.readFileSync('four_pass_sparse_worker.js','utf8'),sandbox);await self.onmessage({data:{file,start_ns:'0',configuration:{min_width_ticks:4}}});return msgs;}
(async()=>{const text=fs.readFileSync('synthetic_ticks.jsonl','utf8');const result=await worker(new Blob([text]));assert.equal(result.at(-1).detector.status,'STOPPED_FIRST_ZONE');tests++;
 const expected=JSON.parse(fs.readFileSync('synthetic_layer.json')).detector;assert.deepEqual(JSON.parse(JSON.stringify(result.at(-1).detector.zone)),expected.zone);tests++;
 const bad=await worker(new Blob(['{"ts_ns":"123","price_tick":1,"sequence":1}\n']));assert.equal(bad.at(-1).detector.status,'ABSTAIN_INPUT');tests++;
 const els={};function element(){return {style:{},hidden:false,textContent:'',value:'0',checked:false,setAttribute(){},appendChild(){},set innerHTML(x){for(const m of x.matchAll(/id="([^"]+)"/g))els[m[1]]=element();}};}
 const document={head:{appendChild(){}},body:{appendChild(){}},createElement:element,getElementById:id=>els[id]};
 let context={asset:'SYNTHETIC_QA',instrument:'SYNTHETIC',contract:'QA',tick_size:1};const window={__EDGELAB_FP4_BRIDGE__:{context:()=>context,x:()=>10,y:p=>p,redraw(){}}};
 vm.runInNewContext(fs.readFileSync('four_pass_sparse_viewer.js','utf8'),{window,document,Worker:function(){},Date,BigInt,Number});
 const layer=JSON.parse(fs.readFileSync('synthetic_layer.json'));await els['fp4-layer'].onchange({target:{files:[{text:async()=>JSON.stringify(layer)}]}});
 let draws=0;const ctx={save(){},restore(){},fillRect(){draws++},beginPath(){},moveTo(){},lineTo(){},stroke(){},fillText(){}};
 const t=Number(BigInt(layer.detector.zone.available_ns))/1e9;window.__EDGELAB_FP4_OVERLAY__.draw(ctx,{to:t+1},100,100);assert.equal(draws,0);tests++;
 els['fp4-clock'].checked=true;window.__EDGELAB_FP4_OVERLAY__.draw(ctx,{to:t-1},100,100);assert.equal(draws,0);tests++;
 window.__EDGELAB_FP4_OVERLAY__.draw(ctx,{to:t+1},100,100);assert.equal(draws,1);tests++;
 context={...context,asset:'OTHER'};window.__EDGELAB_FP4_OVERLAY__.draw(ctx,{to:t+1},100,100);assert.equal(draws,1);assert.match(els['fp4-status'].textContent,/ABSTAIN/);tests++;
 els['fp4-hide'].onclick();context={...context,asset:'SYNTHETIC_QA'};window.__EDGELAB_FP4_OVERLAY__.draw(ctx,{to:t+1},100,100);assert.equal(draws,1);tests++;
 const invalid=JSON.parse(JSON.stringify(layer));invalid.detector.zone.available_ns='bad-time';await els['fp4-layer'].onchange({target:{files:[{text:async()=>JSON.stringify(invalid)}]}});assert.match(els['fp4-status'].textContent,/ABSTAIN/);window.__EDGELAB_FP4_OVERLAY__.draw(ctx,{to:t+1},100,100);assert.equal(draws,1);tests++;
 console.log('PASS integration tests '+tests+'; worker/core parity, clock gating, future suppression, domain,clear,malformed-layer');fs.writeFileSync('integration_evidence.json',JSON.stringify({tests_passed:tests,visual_render_verified:false,browser_worker_simulated_with_node_stream:true},null,2));
})().catch(e=>{console.error(e);process.exit(1)});
