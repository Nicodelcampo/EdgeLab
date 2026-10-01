importScripts('four_pass_sparse.js');
self.onmessage=async function(e){const {file,configuration,start_ns}=e.data;let reader;try{const d=new EdgeLabFourPass.Detector(configuration),start=BigInt(start_ns||'0');reader=file.stream().pipeThrough(new TextDecoderStream()).getReader();let pending='',read=0;
 function line(s){if(!s.trim())return;const r=JSON.parse(s);if(BigInt(String(r.ts_ns))<start)return;read++;d.push(r);}
 while(d.status==='SEARCHING'){const part=await reader.read();if(part.done){if(pending.trim())line(pending);break;}pending+=part.value;let i;
 while((i=pending.indexOf('\n'))>=0){line(pending.slice(0,i));pending=pending.slice(i+1);if(d.status!=='SEARCHING')break;if(read%20000===0)self.postMessage({type:'progress',read:read});}}
 await reader.cancel();self.postMessage({type:'done',read:read,detector:d.snapshot()});
 }catch(err){if(reader)await reader.cancel().catch(()=>{});self.postMessage({type:'error',message:err.message});}};
