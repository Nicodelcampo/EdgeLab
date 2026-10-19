"""Estadísticos de celda, nulo de máximo por sesión (CPU o GPU), réplica cronológica y control de falsos descubrimientos."""
from __future__ import annotations
import numpy as np
from math import erf,sqrt
from .backend import Backend,get_backend

def cell_z(M:np.ndarray,N:np.ndarray,min_trades:int):
    """z = suma de r~ / sqrt(suma de los cuadrados de la suma por sesión). Dos colas. Devuelve (z, S, columnas usadas)."""
    use=np.flatnonzero(N.sum(0)>=min_trades);Mu=M[:,use].astype(np.float64);V=(Mu**2).sum(0);ok=V>0;use=use[ok];Mu=Mu[:,ok];V=V[ok]
    return Mu.sum(0)/np.sqrt(V),Mu.sum(0),use,Mu/np.sqrt(V)

KERNEL_ID="discovery.max_null.sign_flip.v2"
def max_null(Ms:np.ndarray,n_sims:int,seed:int,backend:Backend|None=None,max_matrix_bytes:int=512*1024*1024,one_sided:bool=False)->np.ndarray:
    """Distribución nula del máximo |z| (o z) con signo de cada sesión sorteado +-1. Ms: (D,ncell) ya dividido por sqrt(V).
    La matriz de salida (sorteos x celdas de un bloque, float32) no supera `max_matrix_bytes` (regla de 512 MiB del embudo); las celdas se
    procesan por bloques y los signos de cada lote de sorteos son los MISMOS en todos los bloques, de modo que el resultado no depende del bloqueo."""
    be=backend or get_backend("cpu");xp=be.xp;D,nc=Ms.shape;rng=np.random.default_rng(seed)
    col_block=int(max(1,min(nc,max_matrix_bytes//max(4*D,1))));sims_chunk=int(max(1,min(n_sims,max_matrix_bytes//(4*col_block))))
    blocks=[(c0,min(nc,c0+col_block)) for c0 in range(0,nc,col_block)];dev=[xp.asarray(Ms[:,c0:c1].astype(np.float32)) for c0,c1 in blocks] if len(blocks)<=8 else None
    out=np.full(n_sims,-np.inf,np.float32)
    for a in range(0,n_sims,sims_chunk):
        n=min(sims_chunk,n_sims-a);e=xp.asarray((2*rng.integers(0,2,size=(n,D))-1).astype(np.float32));m=None
        for bi,(c0,c1) in enumerate(blocks):
            A=dev[bi] if dev is not None else xp.asarray(Ms[:,c0:c1].astype(np.float32));r=e@A;v=r.max(1) if one_sided else xp.abs(r).max(1)
            m=v if m is None else xp.maximum(m,v)
        out[a:a+n]=be.to_host(m)
    return out

def p_value(real:float,null:np.ndarray)->float:return float((np.sum(null>=real)+1)/(len(null)+1))
def normal_p(z:np.ndarray)->np.ndarray:
    return np.array([1-erf(abs(x)/sqrt(2)) for x in np.atleast_1d(z)])
def holm(p:np.ndarray)->np.ndarray:
    p=np.asarray(p,float);o=np.argsort(p);adj=np.empty_like(p);run=0.;m=len(p)
    for rank,i in enumerate(o):run=max(run,(m-rank)*p[i]);adj[i]=min(1.,run)
    return adj
def benjamini_hochberg(p:np.ndarray)->np.ndarray:
    """Valores q (control de la tasa de falsos descubrimientos)."""
    p=np.asarray(p,float);m=len(p);o=np.argsort(p);q=np.empty(m);run=1.
    for rank in range(m-1,-1,-1):
        i=o[rank];run=min(run,p[i]*m/(rank+1));q[i]=run
    return q

def scan(M,N,min_trades:int,n_sims:int,seed:int,backend:Backend|None=None)->dict:
    z,S,use,Ms=cell_z(M,N,min_trades)
    if len(z)==0:return {"n_cells":0,"real_max_abs_z":0.,"p_max":1.0,"z":z,"cells":use,"S":S}
    nul=max_null(Ms,n_sims,seed,backend);real=float(np.abs(z).max());pn=normal_p(z)
    return {"n_cells":int(len(z)),"real_max_abs_z":real,"null_max_q95":float(np.quantile(nul,.95)),"null_max_mean":float(nul.mean()),"p_max":p_value(real,nul),
            "z":z,"S":S,"cells":use,"p_normal":pn,"q_bh":benjamini_hochberg(pn)}

def replicate(M,N,is_idx,oos_idx,min_trades:int,top_k:int,n_sims:int,seed:int,backend:Backend|None=None)->list[dict]:
    """Elige las top_k celdas por |z| en las sesiones `is_idx` y las prueba, con signo fijo, en `oos_idx` (unilateral). Holm sobre top_k.
    `is_idx`/`oos_idx`: índices de sesión o máscaras booleanas (p. ej. D0 y D1 del embudo; D2 queda sellado y no se pasa)."""
    is_idx=np.arange(M.shape[0])[is_idx] if np.asarray(is_idx).dtype==bool else np.asarray(is_idx);oos_idx=np.arange(M.shape[0])[oos_idx] if np.asarray(oos_idx).dtype==bool else np.asarray(oos_idx)
    Mi,Ni=M[is_idx],N[is_idx];Mo=M[oos_idx].astype(np.float64);No=N[oos_idx]
    z,S,use,_=cell_z(Mi,Ni,max(5,int(min_trades*len(is_idx)/M.shape[0])));top=np.argsort(-np.abs(z))[:top_k];rng=np.random.default_rng(seed);D=Mo.shape[0]
    E=rng.choice(np.array([-1.,1.]),size=(n_sims,D));res=[]
    for t in top:
        c=int(use[t]);sg=1. if S[t]>0 else -1.;col=Mo[:,c];V=(col**2).sum()
        zo=sg*col.sum()/np.sqrt(V) if V>0 else 0.;nul=sg*(E@col)/np.sqrt(V) if V>0 else np.zeros(n_sims)
        res.append({"cell":c,"sign":sg,"z_is":float(z[t]),"z_oos":float(zo),"p_oos":p_value(zo,nul),"oos_trades":int(No[:,c].sum())})
    adj=holm(np.array([r["p_oos"] for r in res])) if res else np.array([])
    for r,a_ in zip(res,adj):r["p_holm"]=float(a_)
    return res

def staged_scan(M,N,dates,split,spec,backend:Backend|None=None)->dict:
    """Protocolo D0/D1/D2 del embudo: barrido con nulo de máximo en D0; las mejores celdas se replican en D1; D2 permanece SELLADO
    (esta función nunca lo lee: exige el hash del split para construir su máscara en otro proceso)."""
    from edgelab.funnel.splits import mask_for
    m0=mask_for(split,dates,"D0");m1=mask_for(split,dates,"D1")
    r=scan(M[m0],N[m0],max(5,int(spec.min_trades*m0.sum()/len(dates))),spec.n_sims,spec.seed,backend)
    rep=replicate(M,N,m0,m1,spec.min_trades,spec.top_k_replication,20000,spec.seed+1,backend)
    r["D0_sessions"]=int(m0.sum());r["D1_sessions"]=int(m1.sum());r["D2_sealed"]=True;r["split_hash"]=split.split_hash;r["replication"]=rep;r["D0_mask"]=m0;return r
