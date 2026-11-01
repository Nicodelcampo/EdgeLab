"""Motor de Kaggle de la cartera viva (2026-11-01, Nico: «el SV1 tiene que usar Kaggle»).

SV1 no tiene ticks de futuros ni el release de desarrollo en disco. Todo lo que la cartera calcula sobre datos corre como kernel:
- Seguimiento en papel (`papel.actualizar`): etapa ANALIZAR_REGLA en modo SELLADO, con el dataset sellado como única fuente. El kernel
  arma el contexto desde la primera sesión del holdout (calentamiento) y sólo informa operaciones de sesiones >= DESDE, la primera
  sesión forward pendiente (`grilla_generica`, `desde_eval`). El acta del kernel es el pre-registro de la ficha.
- Régimen diario (`diarios`): etapa DIARIO (barras diarias h/l/c por sesión CME, target-free). Desarrollo (< 2026-10-01) desde el
  release, una vez, en caché. Desde 2026-10-01, desde el dataset sellado, cada día.
`Espera` adapta el KaggleRunner a la interfaz lanzar/traer del ciclo. Lanza sin esperar, espera recién en `traer`, así que los kernels
del día corren en paralelo. Verifica que el resultado sea de la versión pedida (mismo HASTA): un slug reusado devolvería la anterior.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

FRONTERA = 20261001
ACTA_REGIMEN = "docs/CARTERA_VIVA.md"


class Espera:
    def __init__(self, run, espera_s: float = 2400, cada_s: float = 30, dormir=time.sleep, reloj=time.time):
        self.run, self.espera_s, self.cada_s, self.dormir, self.reloj = run, espera_s, cada_s, dormir, reloj
        self.pedido: dict = {}
        self.dataset_sellado = getattr(run, "dataset_sellado", None)

    def lanzar(self, spec, etapa, params, periodo) -> str:
        h = self.run.lanzar(spec, etapa, params, periodo); self.pedido[h] = (int(periodo[0]), int(periodo[1]), self.reloj()); return h

    def traer(self, h) -> dict:
        d0, d1, t0 = self.pedido.get(h, (None, None, self.reloj()))
        while True:
            e = self.run.estado(h)
            if e == "complete":
                r = self.run.traer(h)
                if d1 is None or (int(r.get("hasta", -1)) == d1 and int(r.get("desde", -1)) == d0): return r
            elif e == "error":
                raise RuntimeError(f"kernel {h} en error: {getattr(self.run, 'ultimo_detalle', '')}")
            if self.reloj() - t0 > self.espera_s: raise TimeoutError(f"kernel {h} sin terminar en {self.espera_s:.0f} s")
            self.dormir(self.cada_s)


def runners(cfg: dict, carpeta: Path):
    """(runner sellado para papel y régimen reciente, runner de desarrollo para el régimen viejo), los dos con espera."""
    from edgelab.research.embudo_runners import KaggleRunner
    k = cfg.get("kaggle") or {}
    sell = KaggleRunner(dataset_sellado=k.get("dataset_sellado", "nicolasbuttaro/edgelab-holdout-sellado"), carpeta=carpeta / "sellado")
    dev = KaggleRunner(carpeta=carpeta / "desarrollo")
    e = dict(espera_s=k.get("espera_s", 2400), cada_s=k.get("cada_s", 30))
    return Espera(sell, **e), Espera(dev, **e)


def _spec(inst: str) -> dict:
    return dict(cid=f"CARTERA-DIARIO-{inst}".replace(":", "-"), familia="CARTERA_REGIMEN", experimento="edgelab.research.rango_asia0100",
                sensor=inst, ejecucion=inst, cuenta_kaggle="auto")


def _df(r: dict) -> pd.DataFrame:
    d = r.get("diario") or {}
    return pd.DataFrame(dict(fecha=d.get("fecha", []), h=d.get("h", []), l=d.get("l", []), c=d.get("c", []))).astype(
        dict(fecha="int64", h=float, l=float, c=float))


def lanzar_diarios(instrumentos, hasta: int, desde_dev: int, sellado: Espera, desarrollo: Espera, cache: Path, errores: list) -> dict:
    """Lanza sin esperar los kernels DIARIO del día (desarrollo sólo si no está en caché). Devuelve lo pendiente para `traer_diarios`."""
    cache.mkdir(parents=True, exist_ok=True); pend = dict(desarrollo=desarrollo, sellado=sellado, cache=cache, desde_dev=desde_dev,
                                                         instrumentos=list(instrumentos), dev={}, sel={}, errores=errores)
    for inst in instrumentos:
        sp = _spec(inst)
        try:
            if not _cache(pend, inst).exists(): pend["dev"][inst] = desarrollo.lanzar(sp, "DIARIO", {}, [desde_dev, 20260930])
            if hasta >= FRONTERA:
                pend["sel"][inst] = sellado.lanzar(sp, "DIARIO", dict(acta=dict(tipo="cartera_regimen", preregistro=ACTA_REGIMEN, cid=sp["cid"])),
                                                   [FRONTERA, hasta])
        except Exception as ex: errores.append(dict(instrumento=inst, error=f"{type(ex).__name__}: {str(ex)[:200]}"))
    return pend


def _cache(pend, inst) -> Path:
    return pend["cache"] / f"diario_dev_{_spec(inst)['cid']}_{pend['desde_dev']}.json"


def traer_diarios(pend: dict) -> dict:
    """{inst: DataFrame(fecha, h, l, c)}. Un instrumento que falla queda afuera (afinidad neutra) y se informa en `errores`."""
    out = {}
    for inst in pend["instrumentos"]:
        f = _cache(pend, inst)
        try:
            if inst in pend["dev"]: f.write_text(json.dumps(pend["desarrollo"].traer(pend["dev"][inst]), default=float), encoding="utf-8")
            partes = [_df(json.loads(f.read_text(encoding="utf-8")))] if f.exists() else []
            if inst in pend["sel"]: partes.append(_df(pend["sellado"].traer(pend["sel"][inst])))
            if partes: out[inst] = pd.concat(partes).drop_duplicates("fecha", keep="last").sort_values("fecha").reset_index(drop=True)
        except Exception as ex: pend["errores"].append(dict(instrumento=inst, error=f"{type(ex).__name__}: {str(ex)[:200]}"))
    return out
