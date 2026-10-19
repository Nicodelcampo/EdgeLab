/* Synthetic DOM-free tests; no private prices or events. */
const assert=require('node:assert/strict');
const guard=require('../viewer/nt8_bridge/gc_exact4_review_guard.js');
function fixture(){
 const cd=Array.from({length:10},(_,i)=>({time:i,high:100-i,low:98-i,close:99-i}));
 const p=[1,3,5,7].map(i=>[i,cd[i].time,cd[i].high]);
 const b={meta:{tick_size:.1},bar_series:{tick_25:{candles:cd}}};
 const d={schema:'edgelab.gc_exact4.review_layer/1',asset:guard.asset,bar_key:'tick_25',
  targetfree_only:true,outcomes_computed:false,financial_use_certified:false,
  binding:{window:{bars:10,first_bar_time:0,last_bar_time:9}},
  zonas:[{id:'H:1',kind:'H',toques:4,picos:p,members_known_at:[2,4,6,8],
    det_idx:3,det_pico:4,det_i:8,det_t:8,det_precio:cd[8].close,
    targetfree_only:true,outcome_computed:false,financial_use_certified:false,
    publication_metadata_pass:false}]};
 return {d,b};
}
let pass=0;
function check(name,fn){fn();pass++;}
check('valid fixture',()=>{let {d,b}=fixture();assert.equal(guard.validate(d,b,'tick_25',guard.asset),true);});
check('wrong asset',()=>{let {d,b}=fixture();assert.throws(()=>guard.validate(d,b,'tick_25','NQ'));});
check('wrong series',()=>{let {d,b}=fixture();assert.throws(()=>guard.validate(d,b,'tick_150',guard.asset));});
check('wrong schema',()=>{let {d,b}=fixture();d.schema='old';assert.throws(()=>guard.validate(d,b,'tick_25',guard.asset));});
check('five peaks',()=>{let {d,b}=fixture();d.zonas[0].picos.push([8,8,92]);assert.throws(()=>guard.validate(d,b,'tick_25',guard.asset));});
check('trigger not fill',()=>{let {d,b}=fixture();d.zonas[0].det_precio=999;assert.throws(()=>guard.validate(d,b,'tick_25',guard.asset));});
check('bad peak parity',()=>{let {d,b}=fixture();d.zonas[0].picos[0][2]++;assert.throws(()=>guard.validate(d,b,'tick_25',guard.asset));});
check('financial flag',()=>{let {d,b}=fixture();d.financial_use_certified=true;assert.throws(()=>guard.validate(d,b,'tick_25',guard.asset));});
check('bad window',()=>{let {d,b}=fixture();d.binding.window.bars++;assert.throws(()=>guard.validate(d,b,'tick_25',guard.asset));});
check('fail closed',()=>{let {d,b}=fixture();assert.equal(guard.canDraw(d,b,'tick_150',guard.asset),false);});
check('immutable membership',()=>{let {d,b}=fixture();guard.validate(d,b,'tick_25',guard.asset);assert.ok(Object.isFrozen(d.zonas[0].picos));assert.throws(()=>d.zonas[0].picos.push([8,8,92]));});
check('invalid side',()=>{let {d,b}=fixture();d.zonas[0].kind='?';assert.throws(()=>guard.validate(d,b,'tick_25',guard.asset));});
console.log(JSON.stringify({tests:pass,status:'PASS',scope:'SYNTHETIC_GUARD_TESTS'}));