"""Calibración con señal plantada: mide potencia y falsos positivos del propio protocolo.

Falsos positivos: se sortea el signo de cada sesión de los datos reales (nulo exacto por construcción) y se cuenta con qué frecuencia el
protocolo rechaza. Potencia: se suma a una celda al azar un efecto conocido por operación (en desvíos de la celda) y se cuenta la detección."""
from __future__ import annotations
import numpy as np
from .scan import cell_z,max_null,p_value
from .backend import Backend

def false_positive_rate(M,N,min_trades:int,reps:int,n_sims:int,seed:int,alpha:float=0.05,backend:Backend|None=None)->dict:
    rng=np.random.default_rng(seed);rej=0;D=M.shape[0]
    for r in range(reps):
        e=rng.choice(np.array([-1.,1.],np.float32),size=(D,1));z,S,use,Ms=cell_z(M*e,N,min_trades)
        if len(z)==0:continue
        nul=max_null(Ms,n_sims,seed+1+r,backend);rej+=p_value(float(np.abs(z).max()),nul)<=alpha
    return {"reps":reps,"rejections":int(rej),"false_positive_rate":rej/reps,"alpha":alpha}

def power_curve(M,N,min_trades:int,effects_sd:list[float],reps:int,n_sims:int,seed:int,alpha:float=0.05,backend:Backend|None=None)->list[dict]:
    """effects_sd: efecto por operación en desvíos de la celda plantada. Devuelve la tasa de detección (p_max<=alpha) por tamaño.
    La base de cada repetición es la matriz real con el signo de cada sesión sorteado: así la potencia no depende de que los datos reales tengan o no estructura."""
    rng=np.random.default_rng(seed);D=M.shape[0];tot=N.sum(0);cand=np.flatnonzero(tot>=max(min_trades,60));out=[]
    sd_cell=np.sqrt(np.maximum((M.astype(np.float64)**2).sum(0)/np.maximum(tot,1),1e-12))
    for eff in effects_sd:
        det=0;
        for r in range(reps):
            e=rng.choice(np.array([-1.,1.],np.float32),size=(D,1))      # neutraliza cualquier estructura REAL de la base (signos por sesión al azar)
            c=int(rng.choice(cand));M2=(M*e).astype(np.float32);M2[:,c]+=np.float32(eff*sd_cell[c])*N[:,c]
            z,S,use,Ms=cell_z(M2,N,min_trades)
            nul=max_null(Ms,n_sims,seed+7919*(r+1),backend);det+=p_value(float(np.abs(z).max()),nul)<=alpha
        out.append({"effect_sd_per_trade":eff,"detection_rate":det/reps,"reps":reps})
    return out
