const assert=require('node:assert/strict');const fs=require('node:fs');const A=require('./four_pass_sparse.js');let tests=0;const fixtureDetector=options=>new A.Detector({min_width_ticks:4,...(options||{})});
function test(name,fn){fn();tests++;console.log('PASS '+name);}
let seq=0,ts=1754000000000000000n;
function row(p,volume=1,dt=1000000000n){seq++;ts+=dt;return {ts_ns:ts.toString(),sequence:seq,price_tick:p,volume,instrument:'SYNTHETIC',contract:'QA'};}
const cfg={...A.DEFAULTS};function fixed(){return new A.Corridor(10,20,'test',cfg,'0',0,[]);}
function feed(c,ps){for(const p of ps)c.push(row(p));return c;}
test('same edge does not count',()=>{const c=feed(fixed(),[5,10,15,10,5]);assert.equal(c.passes.length,0);assert.equal(c.failed_visits,1);});
test('full traversal counts once',()=>{const c=feed(fixed(),[5,10,15,20,21]);assert.equal(c.passes.length,1);assert.equal(c.rearm,1);});
test('must departX before another traversal',()=>{const c=feed(fixed(),[5,10,20,21,20,10,9]);assert.equal(c.passes.length,1);});
test('exact departure qualifies then return',()=>{const c=feed(fixed(),[5,10,20,21,23,20,10,9]);assert.equal(c.passes.length,2);});
test('four frozen; fifth not appended',()=>{const c=feed(fixed(),[5,10,20,23,20,10,7,10,20,23,20,10,7,10,20,23]);assert.equal(c.passes.length,4);assert.equal(c.retired,true);});
test('jump with no print inside is not traversal',()=>{const c=feed(fixed(),[5,25,5,25]);assert.equal(c.passes.length,0);assert.equal(c.skipped_jumps,3);});
test('failed visits included in commerce',()=>{const c=feed(fixed(),[5,10,15,10,5,10,15,20,23]);assert.equal(c.failed_visits,1);assert.equal(c.metrics.prints,6);});
test('large elapsed gaps no automatic expiry',()=>{const c=fixed();c.push(row(5));c.push(row(10,1,86400n*1000000000n));c.push(row(20));c.push(row(23));assert.equal(c.passes.length,1);});
test('exactNS retained and duplicate time sequenced',()=>{const d=fixtureDetector();const r=row(1);d.push(r);d.push({...r,sequence:r.sequence+1,price_tick:2});assert.equal(d.status,'SEARCHING');assert.equal(d.seen,2);});
test('floatNS rejected',()=>{const d=fixtureDetector();d.push({...row(1),ts_ns:1754000000000000000});assert.equal(d.status,'ABSTAIN_INPUT');});
test('outoforder fails closed',()=>{const d=fixtureDetector();const r=row(1);d.push(r);d.push({...r,sequence:r.sequence-1});assert.equal(d.status,'ABSTAIN_ORDER');});
test('contract change fails closed',()=>{const d=fixtureDetector();d.push(row(1));d.push({...row(2),contract:'ROLL'});assert.equal(d.status,'ABSTAIN_DOMAIN_CHANGE');});
test('declared missing history fails closed',()=>{const d=fixtureDetector();d.push({...row(1),gap:true});assert.equal(d.status,'ABSTAIN_GAP');});
test('missing actualvolume rejected notzeroimputed',()=>{const d=fixtureDetector();const r=row(1);delete r.volume;d.push(r);assert.equal(d.status,'ABSTAIN_INPUT');});
test('badweights rejected',()=>assert.throws(()=>fixtureDetector({weights:{volume:1}})));
test('coldstart not statisticallyqualified',()=>assert.equal(A.assess(fixed()).status,'INSUFFICIENT_REFERENCE'));
test('tiedpercentile neutral not100%',()=>{assert.equal(A.percentile(1,[1,1],true),.5);assert.equal(A.percentile(1,[1,1],false),.5);});
test('more lateral movement means worse rank',()=>assert.equal(A.percentile(10,[0,1,2],true),0));
function fixture(){seq=0;ts=1754000000000000000n;let out=[row(0,100)],p=0;function move(to,v=100,dt=1000000000n){while(p!==to){p+=Math.sign(to-p);out.push(row(p,v,dt));}}
 for(let i=0;i<80;i++){move(20+(i%11));move(0);}
 move(50,1,1000000n);move(0,1,1000000n);move(50,1,1000000n);move(0,1,1000000n);move(150,100);return out;}
const data=fixture();const d=fixtureDetector();for(const r of data)d.push(r);const snap=d.snapshot();
test('discovery finds four actual passes with references',()=>{assert.equal(snap.status,'STOPPED_FIRST_ZONE');assert.equal(snap.zone.passes.length,4);assert.ok(snap.zone.assessment.n_commerce_reference>=32);assert.ok(snap.zone.assessment.width_percentile>=.8);});
test('stop globally ignores even malformedfuture',()=>{const before=d.snapshot();d.push({garbage:true});assert.deepEqual(d.snapshot(),before);});
test('prefix identical tofull, no futurelookup',()=>{const cut=data.findIndex(x=>x.sequence===snap.zone.available_sequence);const x=fixtureDetector();for(const r of data.slice(0,cut+1))x.push(r);assert.deepEqual(x.snapshot(),snap);});
test('all prefixes are stateidentical',()=>{const live=fixtureDetector();for(let i=0;i<data.length;i++){live.push(data[i]);if(i%137===0){const batch=fixtureDetector();for(const r of data.slice(0,i+1))batch.push(r);assert.deepEqual(batch.snapshot(),live.snapshot());}}});
test('translation invariance ticks',()=>{const x=fixtureDetector();for(const r of data)x.push({...r,price_tick:r.price_tick+12345});const z=x.snapshot().zone;assert.equal(z.lo_tick-snap.zone.lo_tick,12345);assert.deepEqual(z.assessment,snap.zone.assessment);});
test('manualreset starts anew',()=>{d.reset();assert.equal(d.status,'SEARCHING');assert.equal(d.zone,null);assert.equal(d.seen,0);});
test('MNQ minimum30ticks independent of rare percentile',()=>{const x=new A.Detector();for(const r of data)x.push({...r,instrument:'MNQ'});const q=x.snapshot();assert.equal(q.resolved_min_width_ticks,30);assert.equal(q.resolved_reversal_ticks,8);assert.ok(x.candidates.every(c=>c.hi-c.lo>=30));if(q.zone)assert.ok(q.zone.hi_tick-q.zone.lo_tick>=30);});
test('MNQ seed discards small bands but keeps small reference widths',()=>{const x=new A.Detector();const rs=Array.from({length:81},(_,i)=>({...row(i),instrument:'MNQ'}));x.push(rs[0]);x.leg=rs;x.seed(rs,rs.at(-1));assert.equal(x.candidates.length,2);assert.ok(x.candidates.every(c=>c.hi-c.lo>=30));assert.ok(x.references[2].some(r=>r.width<30));});
test('unknowninstrument abstains without transferredwidth',()=>{const x=new A.Detector();x.push({...row(1),instrument:'RTY'});assert.equal(x.status,'ABSTAIN_WIDTH_PROFILE');});
test('explicitprofile cannot reduceMNQ below30',()=>{const x=new A.Detector({min_width_ticks:4});x.push({...row(1),instrument:'MNQ'});assert.equal(x.width_floor,30);});
test('transfer uses volatility in native ticks',()=>assert.equal(A.transferMinWidth(30,15,10),20));
test('missingvolatility never fabricated',()=>assert.throws(()=>A.transferMinWidth(30,0,10)));
test('invalidminimum rejected',()=>assert.throws(()=>new A.Detector({min_width_ticks:2})));
fs.writeFileSync('synthetic_ticks.jsonl',data.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync('synthetic_layer.json',JSON.stringify({schema:'edgelab.four_pass_sparse_layer/1',source:'SYNTHETIC_QA_NOT_MARKET_DATA',tick_size:1,start_ns:data[0].ts_ns,asset:'SYNTHETIC_QA',detector:snap},null,2));
fs.writeFileSync('tests_evidence.json',JSON.stringify({tests_passed:tests,synthetic_only:true,prefix_invariant:true,outcomes_computed:false,configuration:A.DEFAULTS},null,2));console.log('TOTAL '+tests);
