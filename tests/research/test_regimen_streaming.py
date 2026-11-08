"""Búsqueda de régimen en flujo (`regimen_offline.buscar_streaming`): elegida y estática idénticas a `walk_forward`, en el observado
y en réplicas del nulo de signo (mismos signos), con memoria de un mes de un cubo (los 82 cubos densos ocupaban ~27 GB)."""
import numpy as np

from edgelab.research import grilla_masiva as GM, regimen_offline as RO


def _cubo(seed, n=6000):
    r = np.random.default_rng(seed)
    meses = [202501, 202502, 202503, 202504, 202505, 202506, 202507]
    dias = np.array([m * 100 + d for m in meses for d in range(1, 23)])
    ses = np.sort(r.choice(dias, n)); P = [GM.Perilla("a", 3, "grupo"), GM.Perilla("b", 3, "ge"), GM.Perilla("c", 2, "eq_any")]
    idx = np.stack([r.integers(0, 3, n), r.integers(0, 3, n), r.integers(0, 2, n)], 1)
    return RO.Cubo(f"c{seed}", P, idx, ses, r.normal(0.02 * (idx[:, 0] == 1), 1.0, n))


def test_streaming_igual_a_walk_forward():
    cubos = [_cubo(s) for s in range(5)]
    V={"A":dict(W=3,min_ops=20,min_dias=10,min_pos=0.4,cada_mes_pos=True,min_dias_mes=3),"C":dict(W=1,min_ops=10,min_dias=5,min_pos=0.3),
       "D":dict(W=2,min_ops=20,min_dias=10,min_pos=0.0)}
    r=RO.buscar_streaming([(c.nombre,(lambda c=c: c)) for c in cubos],V,k=3,B=3,seed=4,min_ops_serie=30,detalle=True)
    D=[RO.series_diarias(c,min_ops=30) for c in cubos]
    nmal=0; ncomp=0
    for v,p in V.items():
        for b in range(4):
            sg=None if b==0 else r["signos"][b]
            o=RO.walk_forward(D,k=3,signo=sg,seed=0,B_azar=5,**p)
            a={f["mes"]:f for f in o["ventanas"]}; s={f["mes"]:f for f in r["filas"][v][b]}
            assert set(a)==set(s),(v,b,sorted(a),sorted(s))
            for m in a:
                for key in ("elegida","estatica","cubos"):
                    x,y=a[m][key],s[m][key]; ncomp+=1
                    if not ((np.isnan(x) and np.isnan(y)) or abs(x-y)<1e-5): nmal+=1
    assert ncomp > 100 and nmal == 0
