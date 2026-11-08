"""Control EXPLORATORIO sintético maxT con la forma de la grilla ORB.

No usa datos de mercado, ni calendarios ni noticias: no certifica el runner ni
los supuestos reales. Ejecutar desde la raíz del repositorio con SciPy/Numba.
"""
from __future__ import annotations
import json
import numpy as np
from scipy.stats import binomtest
from edgelab.research import grilla_masiva as GM

# Fijados antes de ejecutar: 500 semillas nuevas, 160 sesiones, una señal
# ficticia por duración/sesión, alpha de un canal, 299 signos y mínimo 30.
N, FIRST_SEED, SESSIONS, B, ALPHA = 500, 3000, 160, 299, .05
P = [GM.Perilla('duracion',3,'grupo'), GM.Perilla('dia',5,'eq_any'),
     GM.Perilla('hora',4,'eq_any'), GM.Perilla('atr',3,'eq_any')]
TARGET = (1, 5, 4, 3)  # duración 15, sin filtros de día/hora/ATR


def synthetic(seed):
    r = np.random.default_rng(seed)
    session = np.repeat(np.arange(SESSIONS), 3)
    dur = np.tile(np.arange(3), SESSIONS)
    # Día y factores independientes del ruido; no se usa un calendario real.
    day = np.repeat(np.arange(SESSIONS) % 5, 3)
    hour = r.integers(0, 4, len(session))
    atr = r.integers(0, 3, len(session))
    common = r.normal(0, .6, SESSIONS)[session]
    noise = common + r.standard_t(4, len(session)) / np.sqrt(2)
    return [dur, day, hour, atr], session, noise


def run(idx, ses, net, seed):
    st = GM.estadisticas(*GM.tensor(P, idx, net), min_n=30)
    assert st['n'].shape == (3, 6, 5, 4)
    return GM.criba_maxt(P, idx, net, ses, st, B=B, alfa=ALPHA, seed=seed+11), st


def confidence(n):
    ci = binomtest(int(n), N).proportion_ci(confidence_level=.95, method='wilson')
    return {'count':int(n), 'total':N, 'rate':float(n/N), 'wilson95':[ci.low,ci.high]}


def main():
    false = hits = 0
    evaluable = []
    for seed in range(FIRST_SEED,FIRST_SEED+N):
        idx,ses,net = synthetic(seed)
        mt,st = run(idx,ses,net,seed)
        false += mt['n_nominadas'] > 0
        evaluable.append(int(st['evaluable'].sum()))
        # Mismo ruido, ventaja sintética +0.7 sólo en duración 15: comprobar
        # nominación de la celda SIN filtros, no buscar la celda ganadora.
        planted = net + .7 * (idx[0] == 1)
        mt1,_ = run(idx,ses,planted,seed)
        hits += TARGET in mt1['nominadas']
        if (seed-FIRST_SEED+1) % 100 == 0:
            print('simulaciones',seed-FIRST_SEED+1, flush=True)
    out = dict(escenario='sintético simplificado, un canal; sin noticias ni precios reales',
        semillas=[FIRST_SEED,FIRST_SEED+N-1], sesiones=SESSIONS, celdas_nominales=360,
        min_n=30, alfa=ALPHA, signos=B, efecto_plantado=.7, objetivo=list(TARGET),
        nula_global=confidence(false), potencia_objetivo_plantado=confidence(hits),
        celdas_evaluables=dict(min=int(min(evaluable)),mediana=float(np.median(evaluable)),max=int(max(evaluable))))
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
