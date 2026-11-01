"""Operaciones forward de cada estrategia ACTIVA con el MISMO motor que la eligió (`etapas` ANALIZAR_REGLA, `operaciones=True`):
celda, cortes y tope congelados, sobre las sesiones nuevas. El período arranca `calentamiento_dias` antes de la primera sesión pedida
(indicadores con memoria) y sólo se toman operaciones de sesiones posteriores a la última registrada.
`runner`: `embudo_runners.LocalRunner` (o uno con la misma interfaz) con lectores de los datos nuevos del Debian.

Canasta (2026-11-01): una ficha con `regla.celdas` (lista) sigue la canasta igual-ponderada de esas celdas, como la réplica que la
dejó viva (`escalera.canasta_pistas`, `tools/equity_pistas.py`): una observación por sesión con operaciones = suma del neto de todas
las celdas / número de celdas. Una ficha con `regla.celda` sigue una sola celda, una observación por operación.
"""
from __future__ import annotations

from datetime import date, timedelta


def _menos_dias(yyyymmdd: int, dias: int) -> int:
    d = date(yyyymmdd // 10000, yyyymmdd // 100 % 100, yyyymmdd % 100) - timedelta(days=dias)
    return d.year * 10000 + d.month * 100 + d.day


def canasta_por_sesion(filas, k: int) -> list:
    """[(ses, neto)] por operación -> [(ses, suma/k)] por sesión con operaciones (las celdas sin operación aportan 0)."""
    acc = {}
    for s, x in filas: acc[int(s)] = acc.get(int(s), 0.0) + float(x)
    return [(s, v / k) for s, v in sorted(acc.items())]


def actualizar(cartera, runner, hasta: int, calentamiento_dias: int = 45) -> list:
    """Dos pasadas: lanza todas las fichas y después trae, así los kernels de Kaggle del día corren en paralelo. Con un runner
    sellado (`dataset_sellado`, motor de Kaggle) el período empieza en la primera sesión pendiente: el kernel calienta desde el
    inicio del holdout y sólo informa operaciones desde ahí. El acta del kernel es el pre-registro de la ficha."""
    out, lanzadas = [], []
    sellado = getattr(runner, "dataset_sellado", None)
    for f in cartera.activas():
        d0 = f.ultima_ses() + 1
        if d0 > hasta: continue
        r = f.regla; spec = dict(r["spec"], cid=f.cid, cuenta_kaggle=r["spec"].get("cuenta_kaggle", "auto")); celdas = r.get("celdas") or [r["celda"]]
        params = dict(cortes=r["cortes"], celdas=celdas, tope=r.get("tope"), operaciones=True)
        if sellado and r["spec"].get("datasets_extra"):
            out.append(dict(id=f.id, error="necesita almacenes de zonas que no cubren el forward (datasets_extra): sin seguimiento")); continue
        if sellado: params["acta"] = dict(tipo="cartera_forward", preregistro=f.preregistro, cid=f.cid, desde=f.desde)
        periodo = [d0, hasta] if sellado else [_menos_dias(d0, calentamiento_dias), hasta]
        try: lanzadas.append((f, d0, celdas, runner.lanzar(spec, "ANALIZAR_REGLA", params, periodo)))
        except Exception as ex: out.append(dict(id=f.id, error=f"{type(ex).__name__}: {str(ex)[:200]}"))
    for f, d0, celdas, h in lanzadas:
        try: res = runner.traer(h)
        except Exception as ex:                                              # un instrumento sin datos no frena al resto
            out.append(dict(id=f.id, error=f"{type(ex).__name__}: {str(ex)[:200]}")); continue
        o = res.get("operaciones") or {}
        filas = [(s, x) for s, x in zip(o.get("ses", []), o.get("neto", [])) if int(s) >= d0]
        if f.regla.get("celdas"): filas = canasta_por_sesion(filas, len(celdas))
        out.append(cartera.agregar_ops(f.id, filas))
    return out


def lector_mixto(nombre: str, entrada_desarrollo: str, sellado: str | None, preregistro_de: dict):
    """Lector (d0, d1, spec) -> bloques que junta la historia de desarrollo (< 2026-10-01, fuentes de siempre) con los datos nuevos
    sellados (>= 2026-10-01), que sólo se entregan a una estrategia con apertura registrada: el pre-registro de su ficha hace de acta.
    `preregistro_de`: {cid: ruta del pre-registro}."""
    from edgelab.research import fuentes_ticks as F
    lec, tick = F.resolver(nombre); frontera = F.HOLDOUT_PRIMERA_SESION_INT

    def leer(d0, d1, spec):
        if d0 < frontera: yield from lec(d0, min(d1, _menos_dias(frontera, 1)), entrada_desarrollo)
        if d1 >= frontera and sellado:
            a = max(d0, frontera)
            if nombre.startswith("DK:"): yield from F.bloques_spot_sellado(nombre[3:], a, d1, sellado)
            else: yield from F.bloques_nq_sellado(a, d1, sellado, preregistro_de.get(spec.get("cid")), tick)
    return leer, tick
