const fs=require('node:fs'),readline=require('node:readline');const A=require('./four_pass_sparse.js');
async function main(){const args=process.argv.slice(2);function arg(k,def){const i=args.indexOf(k);return i<0?def:args[i+1];}
 const input=arg('--input'),out=arg('--out');if(!input||!out)throw Error('Use --input ticks.jsonl --out layer.json --tick-size0.25 --asset ASSET_ID');
 const size=Number(arg('--tick-size',null));if(!(size>0))throw Error('TICK_SIZE_REQUIRED');
 const cfgPath=arg('--config'),cfg=cfgPath?JSON.parse(fs.readFileSync(cfgPath)):{},minimum=arg('--min-width-ticks');if(minimum!==undefined)cfg.min_width_ticks=Number(minimum);const d=new A.Detector(cfg),start=BigInt(arg('--from-ns','0'));
 const file=fs.createReadStream(input),rl=readline.createInterface({input:file,crlfDelay:Infinity});let rowsRead=0;
 try{for await(const line of rl){if(!line.trim())continue;const r=JSON.parse(line);if(BigInt(String(r.ts_ns))<start)continue;rowsRead++;d.push(r);if(d.status!=='SEARCHING')break;}}
 finally{rl.close();file.destroy();}
 const layer={schema:'edgelab.four_pass_sparse_layer/1',source:'ACTUAL_TICKS_UNCERTIFIED_CLOCK',asset:arg('--asset',''),tick_size:size,start_ns:start.toString(),rows_read:rowsRead,clock_status:'NOT_CERTIFIED',detector:d.snapshot()};fs.writeFileSync(out,JSON.stringify(layer,null,2)+'\n');console.log(JSON.stringify({status:d.status,rows_read:rowsRead,zone:d.zone?.id||null,outcomes_computed:false}));
 if(d.status.startsWith('ABSTAIN'))process.exitCode=2;}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
