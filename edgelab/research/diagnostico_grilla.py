"""Diagnóstico de mecanismo de una grilla y de episodios de una serie (K55/K56, 2026-11-19).

Origen: la noche del 18 al 19-nov se recomendó la «variante rápida» de Z (cubeta 10, EMA 10) leyendo promedios marginales de una grilla:
tenía 4 operaciones en 18 años (las dos perillas eran un solo eje, la severidad del filtro, y en ese extremo el filtro casi nunca se cumple).
A20 mostraba «81/81 variantes positivas» con 1,2 variantes efectivas (3 de 4 perillas inertes). Y la reversión corta se declaró «apagada
desde 2018» cuando el signo lo hacían 3 meses de crisis. Lo encontró una pregunta de Nico, no un gate. Este módulo lo vuelve un paso de la
cadena: `preflight.validar_preregistro` exige la línea «Diagnóstico de mecanismo:» y `tests/test_diagnostico_obligatorio.py` exige las líneas
«Diagnóstico de grilla:» / «Episodios:» en todo RESULTADO nuevo que lea mesetas, PBO, «N/N variantes» o declare una regla apagada.

Cómo se hace bien (el caso Z, `docs/research/z_pico_20261119/RESULTADO_RAPIDA_Y_SEVERIDAD.md`):
  1. Operaciones por celda ANTES de leer su R: una celda con pocas operaciones no es una variante.
  2. Número efectivo de variantes (participación de autovalores de las series mensuales): 81 casi-copias no son 81 pruebas de robustez.
  3. Qué mueve cada perilla (operaciones y R por nivel): una perilla que no cambia nada no aporta; dos perillas que mueven lo mismo son un eje.
  4. Eje de severidad: correlación de rango entre operaciones y R; si existe, la lectura es dosis-respuesta, no «la mejor variante».
  5. Un promedio por época se descompone por meses: si pocos episodios hacen el signo, el veredicto es «pierde en X», no «murió».
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_OPS_ABS = 30                 # una celda con menos operaciones no se lee como variante
FRAC_DEGENERADA = 0.15           # ... ni una con menos del 15 % de la mediana de la grilla
INERTE_REL = 0.05                # perilla inerte: sus niveles cambian < 5 % las operaciones y < 0,02 R la mediana de R
INERTE_R = 0.02


def numero_efectivo(series: pd.DataFrame) -> float:
    """Participación de autovalores de la matriz de correlación de las columnas (variantes) de `series` (filas = meses)."""
    X = series.loc[:, series.std() > 0]
    if X.shape[1] < 2: return float(X.shape[1])
    ev = np.clip(np.linalg.eigvalsh(np.corrcoef(X.T.to_numpy())), 0, None)
    return float(ev.sum() ** 2 / (ev ** 2).sum())


def diagnostico(ops: pd.DataFrame, variante: str = "variante", valor: str = "R", mes: str = "mes", perillas: dict | None = None) -> dict:
    """`ops`: una fila por operación con la variante, su valor (R) y el mes. `perillas`: {nombre: función variante → nivel} (opcional;
    si las variantes son «X_a_b_c» se toman los campos por posición). Devuelve el diagnóstico y la línea de texto para el RESULTADO."""
    n = ops.groupby(variante).size(); r = ops.groupby(variante)[valor].mean()
    corte = max(MIN_OPS_ABS, FRAC_DEGENERADA * float(n.median()))
    degeneradas = sorted(n[n < corte].index.tolist())
    M = ops.groupby([mes, variante])[valor].sum().unstack().fillna(0.0)
    neff = numero_efectivo(M)
    if perillas is None:
        partes = pd.Series(n.index).str.split("_")
        k = int(partes.map(len).min()) - 1 if len(partes) else 0
        perillas = {f"p{i + 1}": (lambda v, i=i: str(v).split("_")[i + 1]) for i in range(k)}
    vivos = n[n >= corte].index
    tabla, inertes = {}, []
    for nom, f in perillas.items():
        niv = pd.Series({v: f(v) for v in vivos})
        g = pd.DataFrame(dict(n=n[vivos], r=r[vivos], nivel=niv)).groupby("nivel").agg(n=("n", "median"), r=("r", "median"))
        tabla[nom] = {str(k2): (int(v.n), round(float(v.r), 4)) for k2, v in g.iterrows()}
        if len(g) > 1 and (g.n.max() - g.n.min()) / max(g.n.max(), 1) < INERTE_REL and (g.r.max() - g.r.min()) < INERTE_R: inertes.append(nom)
    rho = float(pd.Series(n[vivos].to_numpy(float)).corr(pd.Series(r[vivos].to_numpy(float)), method="spearman")) if len(vivos) >= 5 else float("nan")
    d = dict(variantes=int(len(n)), ops_min=int(n.min()), ops_mediana=int(n.median()), ops_max=int(n.max()), degeneradas=degeneradas,
             corte_degenerada=float(corte), numero_efectivo=round(neff, 2), perillas=tabla, perillas_inertes=inertes,
             spearman_ops_R=round(rho, 3) if rho == rho else None)
    d["linea"] = (f"Diagnóstico de grilla: {d['variantes']} variantes; operaciones por celda {d['ops_min']}/{d['ops_mediana']}/{d['ops_max']} "
                  f"(mín/mediana/máx); {len(degeneradas)} celdas casi vacías (< {corte:.0f} op.); número efectivo de variantes {d['numero_efectivo']}; "
                  f"perillas inertes: {', '.join(inertes) or 'ninguna'}; Spearman(operaciones, R) {d['spearman_ops_R']}.")
    return d


def episodios(ops: pd.DataFrame, valor: str = "R", mes: str = "mes", k: int = 3) -> dict:
    """Cuánto del total explican los k peores y los k mejores meses, y el valor medio sin ellos."""
    s = ops.groupby(mes)[valor].agg(["sum", "count"]).sort_values("sum")
    peores, mejores = s.head(k), s.tail(k)
    sin_p = ops[~ops[mes].isin(peores.index)][valor]; sin_m = ops[~ops[mes].isin(mejores.index)][valor]
    d = dict(media=float(ops[valor].mean()), n=int(len(ops)), peores={str(i): round(float(v), 2) for i, v in peores["sum"].items()},
             mejores={str(i): round(float(v), 2) for i, v in mejores["sum"].items()}, media_sin_peores=float(sin_p.mean()) if len(sin_p) else None,
             media_sin_mejores=float(sin_m.mean()) if len(sin_m) else None)
    d["linea"] = (f"Episodios: media {d['media']:+.3f} (n {d['n']}); sin los {k} peores meses {d['media_sin_peores']:+.3f}; sin los {k} mejores "
                  f"{d['media_sin_mejores']:+.3f}; peores {d['peores']}; mejores {d['mejores']}.")
    return d
