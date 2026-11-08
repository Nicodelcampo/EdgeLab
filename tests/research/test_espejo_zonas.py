"""ESPEJO-ZONAS: zonas vivas tomadas por la ida (cantidad, posición), antigüedad, nacidas en la ida, las de más allá y causalidad."""
import numpy as np

from edgelab.research import espejo_zonas as X, grilla_generica as GG, indicadores as I, preflight as PF, sintetico


def _ref_cruce(c, zi, u, arriba):
    out = []
    for z in range(len(zi)):
        r = len(c)
        for j in range(zi[z] + 1, len(c)):
            if (c[j] > u[z]) if arriba else (c[j] < u[z]): r = j; break
        out.append(r)
    return out


def test_primer_cruce_contra_fuerza_bruta():
    rng = np.random.default_rng(3)
    for _ in range(200):
        n = int(rng.integers(1, 50)); c = rng.normal(size=n).round(1); nz = int(rng.integers(0, 20))
        zi = rng.integers(0, n, nz); u = rng.normal(size=nz).round(1)
        for arriba in (True, False):
            assert list(X._primer_cruce(c, zi, u, arriba)) == _ref_cruce(c, zi, u, arriba)


def test_clasificar_bandas_vida_y_mas_alla():
    # A = 100 en la vela 20 (t = 1200 s), ida hasta la 29 con techo 110 (W = 10). Zonas (espacio techo):
    #  z0 [103,104] creada en 2 (18 min antes): vieja con corte de 10 min, viva -> tomada, pos 0,35
    #  z1 [108,109] creada en 15 (5 min antes): reciente, viva -> tomada, pos 0,85
    #  z2 [105,106] creada en 5 pero cruzada en 8 -> no cuenta
    #  z3 [111,112] creada en 10, viva, a 1 de techo (<= 0,25·W) -> más allá cercana
    #  z4 [107,107.5] nacida en la ida (vela 24) -> tomada sólo en las bandas «ida» y «todas»
    #  z5 [95,96] debajo de A -> nunca cuenta
    zi = np.array([2, 5, 10, 15, 24, 3]); near = np.array([103., 105, 111, 108, 107, 95]); far = np.array([104., 106, 112, 109, 107.5, 96])
    cruce = np.array([99, 8, 99, 99, 99, 99]); tz = zi * 60.0; sz = np.zeros(6, np.int64)
    o = np.argsort(zi, kind="stable"); zi, near, far, cruce, tz = zi[o], near[o], far[o], cruce[o], tz[o]
    def cl(banda): return X._clasificar(zi, near, far, cruce, tz, sz, 20, 29, 0, 100.0, 110.0, 0, 1200.0, banda, 400.0, 800.0, 0.25)
    n, pos, m = cl(0); assert (n, m) == (1, 0) and abs(pos - 0.85) < 1e-9      # <= 400 s: z1 (5 min)
    n, pos, m = cl(1); assert (n, m) == (0, 1)                                 # 400–800 s: z3 (10 min), más allá cercana
    n, pos, m = cl(2); assert (n, m) == (1, 0) and abs(pos - 0.35) < 1e-9      # > 800 s: z0 (18 min)
    n, pos, m = cl(3); assert (n, m) == (1, 0) and abs(pos - 0.725) < 1e-9     # nacidas en la ida: z4
    n, pos, m = cl(4); assert (n, m) == (3, 1)                                 # todas: z0, z1, z4 tomadas; z3 más allá


def test_causal_estatico_y_disparos():
    assert PF.estatico(X) == []
    ctx = GG.contexto_m1(sintetico.bloques(dias=10, planta=False, seed=5), tick=0.25, ticks_por_barra=10)
    D = X.disparos(ctx)
    assert len(D) and set(D.ai) == {0, 1, 2, 3, 4} and set(D.zi_ind) == {0, 1}
    assert I.causal(X.disparos, ctx) == []


def test_almacen_liviano(tmp_path, monkeypatch):
    import pandas as pd
    monkeypatch.setenv("ENTRADA", str(tmp_path)); monkeypatch.delenv("SELLADO", raising=False)
    pd.DataFrame(dict(t_ns=[5, 1], lo=[1.0, 2.0], hi=[2.0, 3.0], t_decidida_ns=[9, 0])).to_parquet(tmp_path / "ZONAS_AVZP2_NQ.parquet")
    pd.DataFrame(dict(t_ns=[3], lo=[1.0], hi=[2.0])).to_parquet(tmp_path / "ZONAS_HFT2_NQ_20260101.parquet")
    pd.DataFrame(dict(t_ns=[1], lo=[1.0], hi=[2.0])).to_parquet(tmp_path / "ZONAS_HFT2_NQ_20251001.parquet")
    pd.DataFrame(dict(t_ns=[1, 2], lo=[1.0, 1.0], hi=[2.0, 2.0], zona=[17, 5])).to_parquet(tmp_path / "ZONAS_AVZG_YM.parquet")
    assert X._almacen({"sensor": "NQ"}, "AVZP2").t_ns.tolist() == [9]                     # sin decidir afuera; disponible al decidirse
    assert X._almacen({"sensor": "NQ"}, "HFT2").t_ns.tolist() == [1, 3]                   # bloques trimestrales, ordenados
    assert X._almacen({"sensor": "YM"}, "AVZG").t_ns.tolist() == [1]                      # zona base de YM
    monkeypatch.setenv("SELLADO", "1")
    import pytest
    with pytest.raises(NotImplementedError): X._almacen({"sensor": "NQ"}, "HFT2")


def test_kernel_liviano():
    from pathlib import Path
    from edgelab.research import embudo_runners as R
    for m in ("edgelab/research/espejo_zonas.py", "edgelab/research/espejo_picos2.py"):
        assert not any("prerange" in d or "u1_" in d for d in R.dependencias(m))           # el kernel pasaba el tope de 1 MB
        assert sum(Path(d).stat().st_size for d in set(R.dependencias(m)) | {m}) < 400_000
