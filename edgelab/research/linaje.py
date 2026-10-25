"""Herencia de multiplicidad por linaje (decisión 4 de la revisión del 2026-10-24, aprobada por Nico).

Problema que cierra: U1-CRUZADO figuraba con ~20 pruebas (`AREAS_EXP_1_CRUZADO`) pero salió de un linaje de ~19,4 M
(`AREAS_EXP_1_NQ` + `AREAS_EXP_1_USATECH`). «Familia nueva, contador en cero» es selección sin cobrar.

Regla: toda familia que entra al embudo declara su linaje en `docs/research/LINAJES.jsonl` (append-only, versionado) ANTES de
su DESC: padres y número efectivo heredado. El número efectivo es conservador por defecto: `"bruto"` = todas las pruebas de los
padres en TRIAL_REGISTRY_GLOBAL más lo que ellos heredan (recursivo, sin descuento por correlación). Un número menor (p. ej. Li-Ji
sobre la correlación de los P&L) se acepta sólo con justificación escrita, y queda al lado del bruto. Una corrección es una línea
nueva y sólo puede SUBIR el número (más conservador); bajarlo después de ver resultados sería rescatar.

Dónde muerde (embudo.py):
  - DESC: el q-valor de cada pista se recalcula como si las pruebas heredadas estuvieran en el mismo tamiz (BH con m + N_her,
    π0 = 1): q_linaje = q_BH · (m + N_her) / m. Desde el 2026-10-24 (falsos negativos) es INFORMACIÓN por defecto
    (`linaje_como: "informacion"`): la confirmación se hace en datos nuevos y la controla LORD++, a su propio nivel. Sólo con
    `linaje_como: "compuerta"` (la campaña reusa para confirmar los mismos datos con los que se seleccionó) la pista sigue sólo si
    q_linaje <= 0,10. Las campañas congeladas antes de esa fecha conservan la compuerta (no se afloja con resultados vistos).
  - ACTA: anota la multiplicidad total y el efecto esperado fuera de muestra con el recorte de Harvey-Liu sobre ese total.
Los padres que el libro de ventanas del holdout ya vincula (`relacionadas`) son obligatorios en la declaración.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIBRO = REPO / "docs/research/LINAJES.jsonl"
REGISTRO = REPO / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"


def _jsonl(p: Path) -> list:
    p = Path(p)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


EVALUABLES = REPO / "docs/research/EVALUABLES.jsonl"


def registrar_evaluables(campaign_id: str, familia: str, n_registradas: int, n_evaluables: int, fuente: str, libro: Path = EVALUABLES) -> dict:
    """Después de correr: cuántas de las celdas registradas antes de lanzar tenían datos para poder rechazar (>= MIN_OPS operaciones).
    Una celda que no llega nunca es una prueba con desenlace: no hereda multiplicidad (filtrado independiente: el tamaño de muestra
    no depende del signo del resultado). Append-only; el registro previo (TRIAL_REGISTRY_GLOBAL) no se toca: sigue siendo la cota."""
    if not 0 <= int(n_evaluables) <= int(n_registradas): raise ValueError("0 <= evaluables <= registradas")
    row = dict(campaign_id=campaign_id, family_id=familia, n_registradas=int(n_registradas), n_evaluables=int(n_evaluables), fuente=fuente,
               registrada=time.strftime("%Y-%m-%d"))
    libro = Path(libro); libro.parent.mkdir(parents=True, exist_ok=True)
    with libro.open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def pruebas_propias(registro: Path = REGISTRO, evaluables: Path | None = EVALUABLES) -> dict:
    """Pruebas por familia: las registradas antes de correr, salvo que `EVALUABLES.jsonl` diga cuántas fueron evaluables (decisión
    2026-10-25: el 96-98 % de las celdas de las grillas finas no llega a 30 operaciones y sólo inflaba el linaje heredado)."""
    ev = {r["campaign_id"]: int(r["n_evaluables"]) for r in (_jsonl(evaluables) if evaluables else [])}
    out = {}
    for r in _jsonl(registro):
        n = int(r["n_trials"]); n = min(n, ev[r.get("campaign_id")]) if r.get("campaign_id") in ev else n
        out[r["family_id"]] = out.get(r["family_id"], 0) + n
    return out


def declaracion(familia: str, libro: Path = LIBRO) -> dict | None:
    filas = [r for r in _jsonl(libro) if r.get("familia") == familia]
    return filas[-1] if filas else None


def padres_implicados(familia: str, ventanas: Path | None = None) -> set:
    """Familias cuyas miradas al holdout el libro de ventanas declara heredadas por `familia`."""
    from edgelab.research import holdout_ventanas as HV
    return {r["familia"] for r in HV.leer(ventanas or HV.LIBRO) if r.get("tipo") == "consumida" and familia in r.get("relacionadas", [])}


def bruto(familia: str, libro: Path = LIBRO, registro: Path = REGISTRO, _propias=None, _vistos=None) -> int:
    """Pruebas brutas heredadas: propias de cada ancestro + lo que esos ancestros heredan (sin contar dos veces)."""
    prop = _propias if _propias is not None else pruebas_propias(registro)
    vistos = _vistos if _vistos is not None else {familia}
    d = declaracion(familia, libro); tot = 0
    for p in (d or {}).get("padres", []):
        if p in vistos: continue
        vistos.add(p); tot += prop.get(p, 0) + bruto(p, libro, registro, prop, vistos)
    return tot


def _matriz(ruta):
    """Matriz de P&L (observaciones x pruebas) declarada en el linaje: .npy o .csv, relativa al repo."""
    import numpy as np
    p = Path(ruta); p = p if p.is_absolute() else REPO / p
    if not p.exists(): return None
    return np.load(p) if p.suffix == ".npy" else np.loadtxt(p, delimiter=",", ndmin=2)


def multiplicidad(familia: str, libro: Path = LIBRO, registro: Path = REGISTRO) -> dict:
    """Multiplicidad heredada. Número efectivo (2026-10-24, falsos negativos): con `matriz_pnl` declarada que cubra TODAS las
    pruebas heredadas, Li-Ji sobre la correlación de sus P&L (`escalera.n_efectivo_o_bruto`); si no, el bruto con `aviso`.
    Un entero declarado con `justificacion_descuento` se respeta como antes."""
    from edgelab.funnel.escalera import n_efectivo_o_bruto
    d = declaracion(familia, libro); prop = pruebas_propias(registro)
    b = bruto(familia, libro, registro)
    if d is None:
        return dict(familia=familia, declarada=False, propias=prop.get(familia, 0), bruto_heredado=b, n_heredado=b, metodo_n="bruto",
                    aviso="linaje sin declarar: se cobra el bruto")
    if d["n_efectivo_heredado"] == "bruto":
        ne = n_efectivo_o_bruto(b, _matriz(d["matriz_pnl"]) if d.get("matriz_pnl") else None)
        n, metodo, aviso = int(round(ne["n"])), ne["metodo"], ne["aviso"]
    else:
        n, metodo, aviso = int(d["n_efectivo_heredado"]), "declarado", None
    return dict(familia=familia, declarada=True, padres=d["padres"], propias=prop.get(familia, 0), bruto_heredado=b, n_heredado=n,
                total=prop.get(familia, 0) + n, justificacion=d.get("justificacion", ""), metodo_n=metodo, aviso=aviso)


def problemas(familia: str, libro: Path = LIBRO, ventanas: Path | None = None, registro: Path = REGISTRO) -> list:
    """Vacío = el linaje está declarado y es coherente con el libro de ventanas."""
    d = declaracion(familia, libro)
    if d is None: return [f"la familia {familia} no declaró su linaje en {LIBRO.name} (obligatorio desde 2026-10-24, aunque sea raíz)"]
    e = []
    if (falta := padres_implicados(familia, ventanas) - set(d["padres"])):
        e.append(f"linaje de {familia} incompleto: el libro de ventanas la vincula con {sorted(falta)}")
    n = d["n_efectivo_heredado"]
    if n != "bruto":
        if not isinstance(n, int) or n < 0: e.append(f"n_efectivo_heredado de {familia} debe ser 'bruto' o un entero >= 0")
        elif d["padres"] and n == 0: e.append(f"{familia} tiene padres pero hereda 0 pruebas")
        elif n < (b := bruto(familia, libro, registro)) and not d.get("justificacion_descuento"):
            e.append(f"{familia} hereda {n} < bruto {b} sin `justificacion_descuento`")
    return e


def declarar(familia: str, padres: list, n_efectivo_heredado="bruto", justificacion: str = "", justificacion_descuento: str = "",
             libro: Path = LIBRO, ahora=None, registro: Path = REGISTRO) -> dict:
    """Agrega una declaración. Si ya había una, la nueva no puede heredar menos (sólo más conservadora)."""
    prev = declaracion(familia, libro)
    if prev is not None:
        def num(d): return bruto(familia, libro, registro) if d["n_efectivo_heredado"] == "bruto" else int(d["n_efectivo_heredado"])
        if set(prev["padres"]) - set(padres): raise ValueError("una corrección no puede quitar padres")
        if num(dict(n_efectivo_heredado=n_efectivo_heredado)) < num(prev): raise ValueError("una corrección sólo puede subir el número heredado")
    row = dict(familia=familia, padres=list(padres), n_efectivo_heredado=n_efectivo_heredado, justificacion=justificacion,
               registrada=ahora or time.strftime("%Y-%m-%d"))
    if justificacion_descuento: row["justificacion_descuento"] = justificacion_descuento
    Path(libro).parent.mkdir(parents=True, exist_ok=True)
    with Path(libro).open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def q_con_linaje(q_fdr: float, pi0: float, m: int, n_heredado: int) -> float:
    """q-valor BH (π0 = 1) de la pista si las N heredadas hubieran estado en el mismo tamiz (con p = 1: no cambian el rango).
    q_fdr llega con el π0 de Storey de la campaña; se lo saca para no aplicar π0 sobre pruebas que no se ven."""
    if n_heredado <= 0: return float(q_fdr)
    q_bh = float(q_fdr) / max(float(pi0), 1e-12)
    return float(min(1.0, q_bh * (m + n_heredado) / m))
