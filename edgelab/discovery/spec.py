"""Especificación de la rejilla de búsqueda. Se fija y se hashea ANTES de mirar resultados."""
from __future__ import annotations
from dataclasses import dataclass,field,asdict
import hashlib,json
from pathlib import Path

FEATURE_KINDS={"mom","rng","vwapdev","imb","absorb","effort","spread","emadev"}
OPS={"gt","lt","zgt","zlt","zabs_lt"}

@dataclass(frozen=True)
class Condition:
    feature:str            # p. ej. "mom_15": tipo + ventana en minutos
    op:str                 # gt/lt sobre el valor crudo; zgt/zlt/zabs_lt sobre el z-score causal
    threshold:float=0.0

    def key(self)->str:return f"{self.feature}:{self.op}:{self.threshold:g}"

@dataclass(frozen=True)
class GridSpec:
    name:str
    holds:tuple[int,...]=(15,30,60,120)
    slots_hhmm:tuple[int,...]=tuple(h*100+m for h in range(24) for m in (0,15,30,45))
    conditions:tuple[Condition,...]=()
    include_none:bool=True
    pairs:tuple[tuple[int,int],...]=()      # índices de `conditions` combinados con AND
    min_trades:int=40
    zscore_lookback:int=60                  # sesiones previas para el z causal
    zscore_min_history:int=20
    n_sims:int=20000
    seed:int=20261010
    split:float=0.7
    top_k_replication:int=5
    alpha:float=0.05
    commission_ticks:float=0.0
    max_entry_delay_s:float=120.0
    max_exit_delay_s:float=120.0

    def validate(self)->None:
        for c in self.conditions:
            kind=c.feature.split("_")[0]
            if kind not in FEATURE_KINDS:raise ValueError(f"característica desconocida: {c.feature}")
            if c.op not in OPS:raise ValueError(f"operador desconocido: {c.op}")
            int(c.feature.split("_")[1])
        n=len(self.conditions)
        for i,j in self.pairs:
            if not(0<=i<n and 0<=j<n and i<j):raise ValueError("pares inválidos")
        if not(0.5<=self.split<0.95):raise ValueError("split fuera de rango")
        if self.n_sims<1000:raise ValueError("n_sims demasiado bajo para un nulo de máximo")

    def n_cells(self)->int:
        nc=(1 if self.include_none else 0)+len(self.conditions)+len(self.pairs)
        return len(self.slots_hhmm)*len(self.holds)*nc

def spec_dict(s:GridSpec)->dict:
    d=asdict(s);d["conditions"]=[asdict(c) for c in s.conditions];return d

def spec_hash(s:GridSpec)->str:
    return hashlib.sha256(json.dumps(spec_dict(s),sort_keys=True,separators=(",",":")).encode()).hexdigest()

def load_spec(path:str|Path)->GridSpec:
    d=json.loads(Path(path).read_text())
    d["conditions"]=tuple(Condition(**c) for c in d.get("conditions",[]))
    for k in("holds","slots_hhmm"):
        if k in d:d[k]=tuple(d[k])
    if "pairs" in d:d["pairs"]=tuple(tuple(p) for p in d["pairs"])
    s=GridSpec(**d);s.validate();return s
