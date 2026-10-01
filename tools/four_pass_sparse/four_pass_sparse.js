/* Four-pass sparse corridors v0.1. Tick-only, causal, STOP_FIRST globally. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.EdgeLabFourPass=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const DEFAULTS=Object.freeze({departure_fraction:.25,departure_min_ticks:2,impulse_reversal_ticks:3,impulse_min_ticks:12,
 fractions:[[.125,.875],[.25,.75],[.375,.625]],reference_window:1000,min_reference:32,width_percentile_min:.80,
 sparse_percentile_min:.50,joint_min:.82,size_weight:.55,weights:{volume:.30,prints:.20,time:.30,lateral:.20},max_candidates:4096,max_leg_ticks:2000000});
const clone=x=>JSON.parse(JSON.stringify(x));
function config(x){const c=Object.assign({},DEFAULTS,x||{});c.weights=Object.assign({},DEFAULTS.weights,(x||{}).weights||{});c.fractions=clone((x||{}).fractions||DEFAULTS.fractions);
 for(const k of ['departure_fraction','size_weight','width_percentile_min','sparse_percentile_min','joint_min'])if(!Number.isFinite(c[k])||c[k]<0||c[k]>1)throw Error('INVALID_CONFIG_'+k);
 for(const k of ['departure_min_ticks','impulse_reversal_ticks','impulse_min_ticks','reference_window','min_reference','max_candidates','max_leg_ticks'])if(!Number.isSafeInteger(c[k])||c[k]<1)throw Error('INVALID_CONFIG_'+k);
 if(c.min_reference>c.reference_window)throw Error('REFERENCE_WINDOW_TOO_SMALL');
 if(Object.values(c.weights).some(x=>!Number.isFinite(x)||x<0)||Math.abs(Object.values(c.weights).reduce((a,b)=>a+b,0)-1)>1e-9)throw Error('INVALID_WEIGHTS');
 if(c.fractions.some(x=>x.length!==2||!(x[0]>=0&&x[1]<=1&&x[1]>x[0])))throw Error('INVALID_FRACTION');return c;}
function tick(x){if(!x||x.ts_ns===undefined||!/^\d+$/.test(String(x.ts_ns)))throw Error('EXACT_NS_STRING_REQUIRED');
 if(typeof x.ts_ns==='number'&&!Number.isSafeInteger(x.ts_ns))throw Error('UNSAFE_JS_NS');
 if(!Number.isSafeInteger(x.price_tick)||!Number.isSafeInteger(x.sequence)||x.sequence<0)throw Error('INTEGER_TICKS_SEQUENCE_REQUIRED');
 if(!Number.isFinite(x.volume)||x.volume<=0)throw Error('POSITIVE_ACTUAL_TRADE_VOLUME_REQUIRED');
 if(!x.instrument||!x.contract)throw Error('INSTRUMENT_CONTRACT_REQUIRED');return {ts_ns:String(x.ts_ns),sequence:x.sequence,price_tick:x.price_tick,volume:x.volume,instrument:String(x.instrument),contract:String(x.contract),gap:x.gap===true};}
function percentile(v,refs,low){if(!refs.length)return null;let n=0;for(const x of refs)n+=(x<v?1:x===v?.5:0);return low?1-n/refs.length:n/refs.length;}
function summary(path,lo,hi){let volume=0,prints=0,time=0,travel=0,previous=null,observed=false;for(const r of path){
 const inside=r.price_tick>=lo&&r.price_tick<=hi;if(inside){volume+=r.volume;prints++;observed=true;}
 if(previous){const dt=Number(BigInt(r.ts_ns)-BigInt(previous.ts_ns))/1e9;
 // Conservative left-observed dwell; no interpolation, no phantom trades in jumps.
 if(previous.price_tick>=lo&&previous.price_tick<=hi)time+=dt;
 const a=Math.max(lo,Math.min(hi,previous.price_tick)),b=Math.max(lo,Math.min(hi,r.price_tick));travel+=Math.abs(b-a);}
 previous=r;}
 const w=hi-lo,levels=w+1;return {volume:volume/levels,prints:prints/levels,time:time/levels,lateral:Math.max(0,travel/w-1),observed:observed};}
class Corridor{
 constructor(lo,hi,id,cfg,born,family,refs){if(!(Number.isSafeInteger(lo)&&Number.isSafeInteger(hi)&&hi>lo))throw Error('INVALID_BOUNDS');this.lo=lo;this.hi=hi;this.id=id;this.cfg=cfg;this.born=born;this.family=family;this.refs=refs;this.x=Math.max(cfg.departure_min_ticks,Math.ceil((hi-lo)*cfg.departure_fraction));this.passes=[];this.side=null;this.visit=null;this.rearm=null;this.previous=null;this.metrics={volume:0,prints:0,time:0,travel:0};this.retired=false;this.skipped_jumps=0;this.failed_visits=0;}
 push(r){if(this.retired)return false;const p=r.price_tick,inside=p>=this.lo&&p<=this.hi,side=p<this.lo?-1:p>this.hi?1:0;
 if(this.previous){if(this.previous.price_tick>=this.lo&&this.previous.price_tick<=this.hi)this.metrics.time+=Number(BigInt(r.ts_ns)-BigInt(this.previous.ts_ns))/1e9;
 const a=Math.max(this.lo,Math.min(this.hi,this.previous.price_tick)),b=Math.max(this.lo,Math.min(this.hi,p));this.metrics.travel+=Math.abs(b-a);}
 if(inside){this.metrics.volume+=r.volume;this.metrics.prints++;}
 if(this.rearm!==null){const away=this.rearm===1?p>=this.hi+this.x:p<=this.lo-this.x;if(away){this.side=this.rearm;this.rearm=null;}}
 else if(this.visit){if(side){if(side!==this.visit.from){this.passes.push({entry_ns:this.visit.entry_ns,exit_ns:r.ts_ns,exit_sequence:r.sequence,direction:side,from_sequence:this.visit.from_sequence});this.rearm=side;this.side=null;if((side===1&&p>=this.hi+this.x)||(side===-1&&p<=this.lo-this.x)){this.side=side;this.rearm=null;}}
 else {this.failed_visits++;this.side=side;}this.visit=null;}}
 else if(this.side!==null){if(inside)this.visit={from:this.side,entry_ns:r.ts_ns,from_sequence:r.sequence};else if(side!==this.side){this.skipped_jumps++;this.side=side;}}
 else if(side)this.side=side;
 this.previous=r;if(this.passes.length===4){this.retired=true;return true;}return false;}
 measures(){const w=this.hi-this.lo,n=4,levels=w+1;return {volume:this.metrics.volume/(levels*n),prints:this.metrics.prints/(levels*n),time:this.metrics.time/(levels*n),lateral:Math.max(0,this.metrics.travel/w-n)/n};}
}
function assess(c){const width=c.hi-c.lo,all=c.refs,peers=all.filter(z=>z.width>=width*.5&&z.width<=width*2);
 const result={status:'INSUFFICIENT_REFERENCE',n_size_reference:all.length,n_commerce_reference:peers.length,width_percentile:null,low_commerce_percentile:null,joint:null,metrics:c.measures(),component_percentiles:{}};
 if(all.length<c.cfg.min_reference||peers.length<c.cfg.min_reference)return result;
 const wp=percentile(width,all.map(z=>z.width),false);let sp=0;for(const k of ['volume','prints','time','lateral']){const q=percentile(result.metrics[k],peers.map(z=>z.metrics[k]),true);result.component_percentiles[k]=q;sp+=q*c.cfg.weights[k];}
 const joint=c.cfg.size_weight*wp+(1-c.cfg.size_weight)*sp;
 Object.assign(result,{status:wp>=c.cfg.width_percentile_min&&sp>=c.cfg.sparse_percentile_min&&joint>=c.cfg.joint_min?'QUALIFIED':'REJECTED',width_percentile:wp,low_commerce_percentile:sp,joint});return result;}
class Detector{
 constructor(options){this.cfg=config(options);this.reset();}
 reset(){this.status='SEARCHING';this.zone=null;this.candidates=[];this.references=this.cfg.fractions.map(()=>[]);this.leg=[];this.anchor=null;this.extreme=null;this.direction=0;this.previous=null;this.seen=0;this.impulses=0;this.completed4=0;this.rejected4=0;this.insufficient4=0;this.error=null;}
 snapshot(){return clone({schema:'edgelab.four_pass_sparse/1',status:this.status,zone:this.zone,seen:this.seen,impulses:this.impulses,active_candidates:this.candidates.length,completed4:this.completed4,rejected4:this.rejected4,insufficient4:this.insufficient4,error:this.error,configuration:this.cfg,outcomes_computed:false});}
 seed(impulse,available){const lo=Math.min(impulse[0].price_tick,impulse[impulse.length-1].price_tick),hi=Math.max(impulse[0].price_tick,impulse[impulse.length-1].price_tick),w=hi-lo;
 if(w<this.cfg.impulse_min_ticks)return;
 for(let f=0;f<this.cfg.fractions.length;f++){const a=this.cfg.fractions[f],bottom=Math.ceil(lo+w*a[0]),top=Math.floor(lo+w*a[1]);if(top-bottom<4)continue;
 if(this.candidates.some(z=>z.family===f&&z.lo===bottom&&z.hi===top))continue;
 if(this.candidates.length>=this.cfg.max_candidates){this.status='ABSTAIN_CAPACITY';this.error='No candidate expiration or silent eviction; restart manually';return;}
 const c=new Corridor(bottom,top,'FP4_'+available.sequence+'_'+f,this.cfg,available.ts_ns,f,clone(this.references[f]));
 // First impulse is observed before creation; retrospective geometry only from this causal prefix.
 for(const r of impulse)c.push(r);for(const r of this.leg.filter(r=>r.sequence>impulse[impulse.length-1].sequence))c.push(r);
 this.candidates.push(c);
 }
 // References added AFTER seeding: no self-reference. Single prior impulse passage per family.
 for(let f=0;f<this.cfg.fractions.length;f++){const a=this.cfg.fractions[f],bottom=Math.ceil(lo+w*a[0]),top=Math.floor(lo+w*a[1]);if(top-bottom<4)continue;const metrics=summary(impulse,bottom,top);if(!metrics.observed)continue;
 this.references[f].push({width:top-bottom,metrics:metrics,available_ns:available.ts_ns});if(this.references[f].length>this.cfg.reference_window)this.references[f].shift();}
 }
 push(raw){if(this.status!=='SEARCHING')return false;let r;try{r=tick(raw);}catch(e){this.status='ABSTAIN_INPUT';this.error=e.message;return false;}
 if(r.gap){this.status='ABSTAIN_GAP';this.error='Unobserved intervening path; not a time-based expiry';return false;}
 if(this.previous&&(BigInt(r.ts_ns)<BigInt(this.previous.ts_ns)||r.sequence<=this.previous.sequence)){this.status='ABSTAIN_ORDER';this.error='Time nondecreasing, sequence strictly increasing required';return false;}
 if(this.previous&&(r.contract!==this.previous.contract||r.instrument!==this.previous.instrument)){this.status='ABSTAIN_DOMAIN_CHANGE';this.error='Manual restart per instrument/natural contract required';return false;}
 this.seen++;const ready=[];
 for(const c of this.candidates)if(c.push(r)){this.completed4++;const a=assess(c);if(a.status==='QUALIFIED')ready.push({c,a});else if(a.status==='REJECTED')this.rejected4++;else this.insufficient4++;}
 this.candidates=this.candidates.filter(c=>!c.retired);
 if(ready.length){ready.sort((a,b)=>b.a.joint-a.a.joint||(b.c.hi-b.c.lo)-(a.c.hi-a.c.lo)||a.c.id.localeCompare(b.c.id));const z=ready[0];
 this.zone={id:z.c.id,instrument:r.instrument,contract:r.contract,lo_tick:z.c.lo,hi_tick:z.c.hi,departure_ticks:z.c.x,created_ns:z.c.born,available_ns:r.ts_ns,available_sequence:r.sequence,passes:clone(z.c.passes),assessment:z.a,semantics:'OBSERVED_GEOMETRY_NOT_EDGE',raw_publication:'FOURTH_OBSERVED_EXIT_NOT_EXTERNAL_FEED_CERTIFICATION'};
 this.status='STOPPED_FIRST_ZONE';this.candidates=[];this.previous=r;return true;}
 if(!this.anchor){this.anchor=r;this.extreme=r;this.leg=[r];this.previous=r;return false;}
 this.leg.push(r);if(this.leg.length>this.cfg.max_leg_ticks){this.status='ABSTAIN_CAPACITY';this.error='Impulse path capacity, no silent truncation';return false;}
 if(!this.direction){if(Math.abs(r.price_tick-this.anchor.price_tick)>=this.cfg.impulse_reversal_ticks){this.direction=r.price_tick>this.anchor.price_tick?1:-1;this.extreme=r;}}
 else if((r.price_tick-this.extreme.price_tick)*this.direction>=0)this.extreme=r;
 else if((this.extreme.price_tick-r.price_tick)*this.direction>=this.cfg.impulse_reversal_ticks){
 const end=this.leg.findIndex(z=>z.sequence===this.extreme.sequence),impulse=this.leg.slice(0,end+1);this.impulses++;this.seed(impulse,r);
 this.leg=this.leg.slice(end);this.anchor=this.extreme;this.direction=-this.direction;this.extreme=r;
 }
 this.previous=r;return false;}
}
return {VERSION:'0.1.0',DEFAULTS:DEFAULTS,Detector:Detector,Corridor:Corridor,assess:assess,summary:summary,percentile:percentile};
});
