"""Ticks por contrato -> tensores (sesión x franja x holding) de resultados y máscaras de condiciones.

Convenciones heredadas de la estrategia de referencia: señal en la barra que CIERRA en franja+1 min; entrada en el primer tick con
sello >= franja+2 min (largo al ask, corto al bid); salida en el primer tick con sello >= entrada+hold (lado contrario).
Mejora respecto de las corridas anteriores: GUARDA DE RETRASO. Si el tick usado se aleja más de `max_*_delay_s` de la hora prevista
(huecos de datos, sesiones truncadas) la oportunidad se descarta; no se toma un tick lejano como precio de salida."""
from __future__ import annotations
import numpy as np,pandas as pd
from dataclasses import dataclass
from .data import MIN,tdate_ordinal
from .spec import GridSpec,Condition
from . import features as F

@dataclass
class Tensors:
    dates:np.ndarray            # (D,) fechas de trading (ordinales), ordenadas
    rt:np.ndarray               # (D,S,H) retorno medio-precio del tramo menos la media de la sesión, en ticks; NaN = inválido
    nl:np.ndarray               # (D,S,H) neto largo por libro menos comisión
    ns:np.ndarray               # (D,S,H) neto corto por libro menos comisión
    masks:np.ndarray            # (D,S,K) bool condiciones; K = [none?] + singles + pairs
    cond_keys:list[str]
    slots:tuple[int,...]
    holds:tuple[int,...]
    meta:dict

def slot_grid(cal_dates:np.ndarray,slots_hhmm:tuple[int,...])->np.ndarray:
    """UTC ns de cada franja CT para cada fecha de calendario (D,S); NaT (-> -1) en huecos de cambio de hora."""
    base=(cal_dates-719163).astype("datetime64[D]").astype("datetime64[m]")
    offs=np.array([(h//100)*60+h%100 for h in slots_hhmm]).astype("timedelta64[m]")
    naive=(base[:,None]+offs[None,:]).reshape(-1).astype("datetime64[ns]")
    loc=pd.DatetimeIndex(naive).tz_localize("America/Chicago",ambiguous="NaT",nonexistent="NaT").tz_convert("UTC")
    ns=np.where(loc.isna(),-1,loc.asi8);return ns.reshape(len(cal_dates),len(slots_hhmm))

def session_end_ns(trade_dates:np.ndarray)->np.ndarray:
    """Fin de la sesión CME de cada fecha de trading: 16:00 CT de esa fecha (UTC ns)."""
    base=pd.DatetimeIndex((trade_dates-719163).astype("datetime64[D]").astype("datetime64[ns]"))+pd.Timedelta(hours=16)
    return base.tz_localize("America/Chicago",ambiguous="NaT",nonexistent="NaT").tz_convert("UTC").asi8

def _conditions_list(spec:GridSpec):
    keys=[];base=[]
    if spec.include_none:keys.append("none")
    for c in spec.conditions:keys.append(c.key());base.append(c)
    for i,j in spec.pairs:keys.append(f"{spec.conditions[i].key()}&{spec.conditions[j].key()}")
    return keys

def _apply(c:Condition,raw:dict,z:dict)->np.ndarray:
    if c.op in("gt","lt"):
        x=raw[c.feature];return (x>c.threshold) if c.op=="gt" else (x<c.threshold)
    x=z[c.feature]
    if c.op=="zgt":return x>c.threshold
    if c.op=="zlt":return x<c.threshold
    return np.abs(x)<c.threshold

def contract_rows(spec:GridSpec,tk:dict,bars:dict)->dict:
    """Parte que lee ticks, independiente de la familia y de la serie continua: para TODAS las franjas de un contrato calcula la entrada
    y las salidas por libro. Resultado compacto (filas = franjas del calendario del contrato) que se puede guardar y reutilizar.
    Clave de cada fila: (fecha de trading `td`, índice de franja `sl`). No aplica la máscara de barra ni la serie continua: eso es del ensamblado."""
    S=len(spec.slots_hhmm);H=len(spec.holds);td_b=tdate_ordinal(bars["t"]);cal=np.arange(int(td_b.min())-1,int(td_b.max())+1,dtype=np.int64)
    G=slot_grid(cal,spec.slots_hhmm);flat=G.reshape(-1);ok0=flat>0;sl_all=np.tile(np.arange(S),len(cal))
    b0=flat[ok0];sl=sl_all[ok0];b1=b0+MIN;E=b0+2*MIN;td=tdate_ordinal(b1);send=session_end_ns(td)
    ts=tk["ts_utc_ns"];bid=tk["bid_ticks"].astype(np.float64);ask=tk["ask_ticks"].astype(np.float64);mid=(bid+ask)/2
    ie=np.searchsorted(ts,E);ie_c=np.minimum(ie,len(ts)-1);ok_e=(ie<len(ts))&((ts[ie_c]-E)<=spec.max_entry_delay_s*1e9)
    n=len(b1);rt=np.full((n,H),np.nan,np.float32);nl=np.full_like(rt,np.nan);ns=np.full_like(rt,np.nan);exit_fail=np.zeros((n,H),bool)
    for hi,h in enumerate(spec.holds):
        X=E+h*MIN;ix=np.searchsorted(ts,X);ix_c=np.minimum(ix,len(ts)-1)
        ok_x=(ix<len(ts))&((ts[ix_c]-X)<=spec.max_exit_delay_s*1e9)&(X<=send);exit_fail[:,hi]=ok_e&~ok_x;ok=ok_e&ok_x
        r=mid[ix_c]-mid[ie_c];L=bid[ix_c]-ask[ie_c]-spec.commission_ticks;Sh=bid[ie_c]-ask[ix_c]-spec.commission_ticks
        rt[ok,hi]=r[ok];nl[ok,hi]=L[ok];ns[ok,hi]=Sh[ok]
    has=F.compute(bars,b1,set())[1]
    return {"td":td,"sl":sl.astype(np.int16),"b1":b1,"has":has,"entry_fail":~ok_e,"exit_fail":exit_fail,"rt":rt,"nl":nl,"ns":ns}

def _mine(rows:dict,elig:dict[int,int],ci:int,dates:np.ndarray):
    """Filas de un contrato que pertenecen a sesiones elegibles de ese contrato: (máscara de filas, índice de fecha)."""
    td=rows["td"];di=np.searchsorted(dates,td);inr=(di<len(dates))&(dates[np.minimum(di,len(dates)-1)]==td);m=np.zeros(len(td),bool)
    if inr.any():m[inr]=np.array([elig[int(dates[k])]==ci for k in di[inr]])
    return m,di

def assemble(spec:GridSpec,rows:dict[str,dict],order:list[str],elig:dict[int,int])->dict:
    """Une las filas de cada contrato según la serie continua (`elig`): tensores (sesión, franja, holding) con la media de la sesión restada."""
    S=len(spec.slots_hhmm);H=len(spec.holds);dates=np.array(sorted(elig));D=len(dates)
    if D==0:raise ValueError("sin sesiones elegibles")
    rt=np.full((D,S,H),np.nan,np.float32);nl=np.full_like(rt,np.nan);ns=np.full_like(rt,np.nan);has_b1=np.zeros((D,S),bool);drop={"entry_delay":0,"exit_delay":0,"no_b1":0}
    for ci,c in enumerate(order):
        if c not in rows:continue
        R=rows[c];m,di=_mine(R,elig,ci,dates)
        if not m.any():continue
        dd=di[m];ss=R["sl"][m].astype(int);has=R["has"][m];has_b1[dd,ss]=has;drop["entry_delay"]+=int(R["entry_fail"][m].sum());drop["exit_delay"]+=int(R["exit_fail"][m].sum())
        for hi in range(H):
            ok=has&np.isfinite(R["rt"][m,hi]);rt[dd[ok],ss[ok],hi]=R["rt"][m,hi][ok];nl[dd[ok],ss[ok],hi]=R["nl"][m,hi][ok];ns[dd[ok],ss[ok],hi]=R["ns"][m,hi][ok]
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",RuntimeWarning);mu=np.nanmean(rt,axis=1,keepdims=True)
    return {"dates":dates,"rt":rt-mu,"nl":nl,"ns":ns,"has_b1":has_b1,"drop":drop}

def build_masks(spec:GridSpec,bars:dict[str,dict],rows:dict[str,dict],order:list[str],elig:dict[int,int],fills:dict)->Tensors:
    """Características causales (solo con barras) y máscaras de condición de la familia."""
    S=len(spec.slots_hhmm);dates=fills["dates"];D=len(dates);has_b1=fills["has_b1"];names={c.feature for c in spec.conditions};raw={n:np.full((D,S),np.nan) for n in names}
    for ci,c in enumerate(order):
        if c not in rows or not names:continue
        R=rows[c];m,di=_mine(R,elig,ci,dates)
        if not m.any():continue
        fr,_=F.compute(bars[c],R["b1"][m],names)
        for n in names:raw[n][di[m],R["sl"][m].astype(int)]=fr[n]
    z={n:F.causal_z(raw[n],spec.zscore_lookback,spec.zscore_min_history) for n in names}
    keys=_conditions_list(spec);K=len(keys);masks=np.zeros((D,S,K),bool);k=0
    if spec.include_none:masks[:,:,0]=True;k=1
    single=[]
    for c in spec.conditions:m=_apply(c,raw,z)&has_b1;masks[:,:,k]=m;single.append(m);k+=1
    for i,j in spec.pairs:masks[:,:,k]=single[i]&single[j];k+=1
    return Tensors(dates,fills["rt"],fills["nl"],fills["ns"],masks,keys,spec.slots_hhmm,spec.holds,{"dropped":fills["drop"],"sessions":D,"cells":D and S*len(spec.holds)*K})

def build(spec:GridSpec,ticks:dict[str,dict],bars:dict[str,dict],order:list[str],segs,elig:dict[int,int],rows:dict[str,dict]|None=None)->Tensors:
    """Camino completo. Con `rows` (precalculadas, p. ej. del caché) no se leen los ticks: `ticks` puede ser None."""
    spec.validate()
    if rows is None:rows={c:contract_rows(spec,ticks[c],bars[c]) for c in order if c in ticks}
    fills=assemble(spec,rows,order,elig);return build_masks(spec,bars,rows,order,elig,fills)

def cell_matrices(T:Tensors,k_sel:slice|np.ndarray|None=None):
    """M[d,cell]=rt*mask (suma de la sesión), N[d,cell]=nº de operaciones. cell=(slot*H+hold)*K+cond."""
    D,S,H=T.rt.shape;masks=T.masks if k_sel is None else T.masks[:,:,k_sel];K=masks.shape[2]
    valid=np.isfinite(T.rt);r=np.where(valid,T.rt,0.).astype(np.float32)
    M=(r[:,:,:,None]*masks[:,:,None,:]).reshape(D,S*H*K);N=(valid[:,:,:,None]&masks[:,:,None,:]).reshape(D,S*H*K).astype(np.float32)
    return M,N
def decode(T:Tensors,cell:int):
    S,H,K=len(T.slots),len(T.holds),len(T.cond_keys);k=cell%K;h=(cell//K)%H;s=cell//(K*H);return {"slot":T.slots[s],"hold":T.holds[h],"cond":T.cond_keys[k]}

def pool_cells(parts):
    """Combina activos que comparten la misma rejilla: suma por fecha de trading las matrices M y N (cada activo en sus ticks: se usa solo
    cuando la agrupación se fijó de antemano, p. ej. 6E con 6J, mismo mercado de divisas). parts: lista de (fechas, M, N). Devuelve (fechas, M, N)."""
    alld=np.unique(np.concatenate([d for d,_,_ in parts]));nc=parts[0][1].shape[1]
    Mp=np.zeros((len(alld),nc),np.float32);Np=np.zeros((len(alld),nc),np.float32)
    for d,M,N in parts:
        if M.shape[1]!=nc:raise ValueError("rejillas distintas")
        i=np.searchsorted(alld,d);Mp[i]+=M;Np[i]+=N
    return alld,Mp,Np
