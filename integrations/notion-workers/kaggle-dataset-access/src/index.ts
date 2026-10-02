import { CREDENTIAL_VALUE, Worker } from "@notionhq/workers"
import { j } from "@notionhq/workers/schema-builder"

const worker = new Worker()
export default worker
const API = "https://www.kaggle.com/api/v1"

worker.credential("KAGGLE_API_TOKEN", { network: [{ domain: "www.kaggle.com", transform: [{ headers: { Authorization: `Bearer ${CREDENTIAL_VALUE}` } }] }, { domain: "api.kaggle.com", transform: [{ headers: { Authorization: `Bearer ${CREDENTIAL_VALUE}` } }] }] })

type J = string | number | boolean | null | J[] | { [k: string]: J }
function json(v: unknown): J { return JSON.parse(JSON.stringify(v)) as J }
function parts(ref: string): [string,string] { const m=ref.trim().match(/^([\w.-]+)\/([\w.-]+)$/); if(!m) throw new Error("Use owner/dataset"); return [m[1],m[2]] }
async function get(path:string, params:Record<string,string>={}) { const q=new URLSearchParams(params); const r=await fetch(`${API}${path}${q.size?`?${q}`:""}`,{headers:{Accept:"application/json"}}); if(!r.ok) throw new Error(`Kaggle ${r.status}: ${(await r.text()).slice(0,500)}`); return json(await r.json()) }

worker.tool("searchKaggleDatasets", {
 title:"Search Kaggle datasets", description:"Search public and accessible Kaggle datasets.",
 schema:j.object({query:j.string(),maxResults:j.number().nullable(),sortBy:j.string().nullable()}),
 execute:async({query,maxResults,sortBy})=>{ const d=await get("/datasets/list",{search:query,sortBy:sortBy??"updated",page:"1"}); return {results:Array.isArray(d)?d.slice(0,Math.min(50,maxResults??20)):[]} }
})

worker.tool("listMyKaggleDatasets", {
 title:"List my Kaggle datasets", description:"List datasets owned by or shared with the authenticated Kaggle account, including private datasets.",
 schema:j.object({query:j.string().nullable(),page:j.number().nullable()}),
 execute:async({query,page})=>{ const p:Record<string,string>={group:"my",sortBy:"updated",page:String(Math.max(1,page??1))}; if(query) p.search=query; const d=await get("/datasets/list",p); return {results:Array.isArray(d)?d:[]} }
})

worker.tool("inspectKaggleDataset", {
 title:"Inspect a Kaggle dataset", description:"Return metadata and files for owner/dataset.", schema:j.object({dataset:j.string()}),
 execute:async({dataset})=>{const[o,s]=parts(dataset); const p=`/${encodeURIComponent(o)}/${encodeURIComponent(s)}`; const [metadata,files]=await Promise.all([get(`/datasets/view${p}`),get(`/datasets/list${p}`)]); return {dataset,metadata,files} }
})

worker.tool("readKaggleDatasetFile", {
 title:"Read a Kaggle dataset file", description:"Read a bounded text preview from a dataset file.",
 schema:j.object({dataset:j.string(),file:j.string(),maxBytes:j.number().nullable()}),
 execute:async({dataset,file,maxBytes})=>{const[o,s]=parts(dataset); const f=file.replace(/^\/+/,""); if(!f||f.includes(".."))throw new Error("Invalid file"); const n=Math.max(1,Math.min(500000,maxBytes??200000)); const u=new URL(`${API}/datasets/download/${encodeURIComponent(o)}/${encodeURIComponent(s)}`); u.searchParams.set("filename",f); const r=await fetch(u,{headers:{Range:`bytes=0-${n}`},redirect:"follow"}); if(!r.ok)throw new Error(`Kaggle ${r.status}: ${(await r.text()).slice(0,500)}`); const b=new Uint8Array(await r.arrayBuffer()); const x=b.slice(0,n); if(x[0]===0x50&&x[1]===0x4b)throw new Error("ZIP returned; choose an individual text file"); return {dataset,file:f,contentType:r.headers.get("content-type"),bytesReturned:x.length,truncated:b.length>x.length||x.length>=n,content:new TextDecoder().decode(x)} }
})

worker.tool("listKaggleDatasetFiles", {
 title:"List Kaggle dataset files", description:"List files in a Kaggle dataset with pagination.",
 schema:j.object({dataset:j.string(),pageSize:j.number().nullable(),pageToken:j.string().nullable()}),
 execute:async({dataset,pageSize,pageToken})=>{const[o,s]=parts(dataset); const p:Record<string,string>={pageSize:String(Math.max(1,Math.min(200,pageSize??100)))}; if(pageToken)p.pageToken=pageToken; return get(`/datasets/list/${encodeURIComponent(o)}/${encodeURIComponent(s)}`,p)}
})

worker.tool("getKaggleDatasetFileUrl", {
 title:"Get Kaggle dataset file download URL", description:"Create a short-lived signed download URL for one exact Kaggle dataset file.",
 schema:j.object({dataset:j.string(),file:j.string()}),
 execute:async({dataset,file})=>{const[o,s]=parts(dataset); const f=file.replace(/^\/+/,""); if(!f||f.includes(".."))throw new Error("Invalid file"); const u=new URL(`${API}/datasets/download/${encodeURIComponent(o)}/${encodeURIComponent(s)}`); u.searchParams.set("filename",f); const r=await fetch(u,{redirect:"manual"}); if(r.status>=300&&r.status<400){const location=r.headers.get("location"); if(!location)throw new Error("Kaggle redirect had no Location header"); return {dataset,file:f,url:location}} if(!r.ok)throw new Error(`Kaggle ${r.status}: ${(await r.text()).slice(0,500)}`); return {dataset,file:f,url:r.url}
 }
})

worker.tool("getKaggleDatasetArchiveUrl", {
 title:"Get Kaggle dataset archive URL", description:"Create a short-lived signed URL for a complete Kaggle dataset archive.",
 schema:j.object({dataset:j.string()}),
 execute:async({dataset})=>{const[o,s]=parts(dataset); const r=await fetch(`${API}/datasets/download/${encodeURIComponent(o)}/${encodeURIComponent(s)}`,{redirect:"manual"}); if(r.status>=300&&r.status<400){const location=r.headers.get("location"); if(!location)throw new Error("Kaggle redirect had no Location header"); return {dataset,url:location}} if(!r.ok)throw new Error(`Kaggle ${r.status}: ${(await r.text()).slice(0,500)}`); return {dataset,url:r.url}}
})


async function rpc(service:string, method:string, body:Record<string,J>) {
 const r=await fetch(`https://api.kaggle.com/v1/${service}/${method}`,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(body)});
 if(!r.ok)throw new Error(`Kaggle RPC ${r.status}: ${(await r.text()).slice(0,1000)}`);
 return json(await r.json())
}

worker.tool("pushKaggleKernel", {
 title:"Push a private Kaggle kernel", description:"Create or update a private Kaggle Python script and start it on CPU or GPU.",
 schema:j.object({id:j.string(),title:j.string(),script:j.string(),accelerator:j.string().nullable(),datasetSourcesCsv:j.string().nullable()}),
 execute:async({id,title,script,accelerator,datasetSourcesCsv})=>{
  const acc=(accelerator??"cpu").toLowerCase(); if(!["cpu","gpu"].includes(acc))throw new Error("accelerator must be cpu or gpu");
  const sources=(datasetSourcesCsv??"").split(",").map(x=>x.trim()).filter(Boolean);
  return rpc("kernels.KernelsApiService","SaveKernel",{slug:id,newTitle:title,text:script,language:"python",kernelType:"script",datasetDataSources:sources,kernelDataSources:[],competitionDataSources:[],modelDataSources:[],categoryIds:[],isPrivate:true,enableGpu:acc==="gpu",enableTpu:false,enableInternet:false,sessionTimeoutSeconds:3600})
 }
})

worker.tool("getKaggleKernelStatus", {
 title:"Get Kaggle kernel status", description:"Return the execution status of a Kaggle kernel.",
 schema:j.object({owner:j.string(),slug:j.string(),versionLabel:j.string().nullable()}),
 execute:async({owner,slug,versionLabel})=>rpc("kernels.KernelsApiService","GetKernelSessionStatus",{userName:owner,kernelSlug:slug,...(versionLabel?{versionLabel}:{})})
})
