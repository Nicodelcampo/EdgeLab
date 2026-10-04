"""Estadísticos de celda, nulo de máximo por sesión (CPU o GPU), réplica cronológica y control de falsos descubrimientos."""
from __future__ import annotations
import numpy as np
from math import erf,sqrt
from .backend import Backend,get_backend

def cell_z(M:np.ndarray,N:np.ndarray,min_trades:int):
    """z = suma de r~ / sqrt(suma de los cuadrados de la suma por sesión). Dos colas. Devuelve (z, S, columnas usadas)."""
    use=np.flatnonzero(N.sum(0)>=min_trades);Mu=M[:,use].astype(np.float64);V=(Mu**2).sum(0);ok=V>0;use=use[ok];Mu=Mu[:,ok];V=V[ok]
    return Mu.sum(0)/np.sqrt(V),Mu.sum(0),use,Mu/np.sqrt(V)

def max_null(Ms:np.ndarray,n_sims:int,seed:int,backend:Backend|None=None,chunk:int=256,one_sided:bool=False)->np.ndarray:
    """Distribución nula del máximo |z| (o z) con signo de cada sesión sorteado ±1. Ms: (D,ncell) ya dividido por sqrt(V)."""
    be=backend or get_backend("cpu");xp=be.xp;D,nc=Ms.shape;A=xp.asarray(Ms.astype(np.float32));out=np.empty(n_sims,np.float32)
    rng=np.random.default_rng(seed);step=max(1,min(chunk,int(2e8//max(nc,1))))
    for a in range(0,n_sims,step):
        n=min(step,n_sims-a);e=xp.asarray(rng.choice(np.array([-1.,1.],np.float32),size=(n,D)));r=e@A
        out[a:a+n]=be.to_host((r.max(1) if one_sided else xp.abs(r).max(1)))
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

def replicate(M,N,sessions_cut:int,min_trades:int,top_k:int,n_sims:int,seed:int,backend:Backend|None=None)->list[dict]:
    """Elige las top_k celdas por |z| en las primeras sesiones y las prueba, con signo fijo, en las siguientes (unilateral). Holm sobre top_k."""
    Mi,Ni=M[:sessions_cut],N[:sessions_cut];Mo=M[sessions_cut:].astype(np.float64)
    z,S,use,_=cell_z(Mi,Ni,max(10,int(min_trades*sessions_cut/M.shape[0])));top=np.argsort(-np.abs(z))[:top_k];rng=np.random.default_rng(seed);D=Mo.shape[0]
    E=rng.choice(np.array([-1.,1.]),size=(n_sims,D));res=[]
    for t in top:
        c=int(use[t]);sg=1. if S[t]>0 else -1.;col=Mo[:,c];V=(col**2).sum()
        zo=sg*col.sum()/np.sqrt(V) if V>0 else 0.;nul=sg*(E@col)/np.sqrt(V) if V>0 else np.zeros(n_sims)
        res.append({"cell":c,"sign":sg,"z_is":float(z[t]),"z_oos":float(zo),"p_oos":p_value(zo,nul),"oos_trades":int(N[sessions_cut:,c].sum())})
    adj=holm(np.array([r["p_oos"] for r in res]))
    for r,a in zip(res,adj):r["p_holm"]=float(a)
    return res
