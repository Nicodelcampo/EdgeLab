"""Un titular por familia y meseta de vecinas (EF3 del embudo): evita la selección del mejor entre un producto cartesiano."""
from __future__ import annotations
import numpy as np

def family_of(cond_key:str)->str:
    if cond_key=="none":return "none"
    if "&" in cond_key:
        kinds=sorted(k.split(":")[0].split("_")[0] for k in cond_key.split("&"));return "pair:"+"+".join(kinds)
    return cond_key.split(":")[0].split("_")[0]

def cell_parts(cell:int,S:int,H:int,K:int):return cell//(K*H),(cell//K)%H,cell%K   # franja, holding, condición

def headlines(z:np.ndarray,cells:np.ndarray,cond_keys:list[str],S:int,H:int,min_neighbors:int=3)->list[dict]:
    """Para cada familia, la celda de mayor |z| y la fracción de vecinas (franja +-1, holding +-1, misma condición) con el mismo signo."""
    K=len(cond_keys);zmap=dict(zip(cells.tolist(),z.tolist()));best={}
    for c,zz in zip(cells.tolist(),z.tolist()):
        s,h,k=cell_parts(c,S,H,K);f=family_of(cond_keys[k])
        if f not in best or abs(zz)>abs(best[f][1]):best[f]=(c,zz)
    out=[]
    for f,(c,zz) in sorted(best.items(),key=lambda kv:-abs(kv[1][1])):
        s,h,k=cell_parts(c,S,H,K);nb=[]
        for ds,dh in((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)):
            s2,h2=s+ds,h+dh
            if 0<=s2<S and 0<=h2<H:
                c2=(s2*H+h2)*K+k
                if c2 in zmap:nb.append(zmap[c2])
        same=sum(1 for v in nb if np.sign(v)==np.sign(zz))
        out.append({"family":f,"cell":int(c),"z":float(zz),"slot_idx":s,"hold_idx":h,"cond":cond_keys[k],"neighbors":len(nb),"same_sign":int(same),"plateau":bool(len(nb)>=min_neighbors and same/len(nb)>=0.75)})
    return out
