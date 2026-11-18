"""Ventanas del holdout ya consumidas y aperturas por familia (revisión del 2026-10-24).

Una mirada al holdout, exploratoria o confirmatoria, CONSUME las sesiones que vio para su familia y para las familias que
derivan de ella (diseño informado por ese resultado). Este libro (append-only, versionado en el repo) lo hace cumplir:
  - `consumida`: familia, desde, hasta (YYYYMMDD) y `relacionadas` (familias cuyo diseño heredó la mirada);
  - `apertura`: la apertura confirmatoria de una familia (una sola por familia, la registra el embudo al escribir el acta);
  - `anulacion` (2026-10-26, decisión de Nico): anula una apertura ANTES de mirar dato alguno del holdout (p. ej. registrada sin
    potencia). La familia recupera su apertura; la anulación queda escrita con su motivo. Nunca después de mirar.
`problemas(familia, desde, cid)` devuelve por qué una apertura NO puede hacerse; vacío = permitida.
Mover una ventana hacia adelante protege más; ningún registro se borra ni se edita (una corrección es una línea nueva).
"""
from __future__ import annotations
import json, time
from pathlib import Path

LIBRO = Path(__file__).resolve().parents[2] / "docs/research/HOLDOUT_VENTANAS.jsonl"


def leer(libro: Path = LIBRO) -> list:
    p = Path(libro)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def reuso_autorizado(familia: str, libro: Path = LIBRO) -> dict | None:
    """Decisión de Nico (2026-10-24): una familia cuya regla se congeló ANTES de la mirada exploratoria y no cambió después puede
    reusar esas sesiones, sólo con un estadístico válido ante miradas (e-proceso de edgelab/funnel/secuencial.py) que arranca en
    la frontera. Se reporta siempre también el resultado sin las sesiones miradas."""
    rs = [r for r in leer(libro) if r.get("tipo") == "reuso_autorizado" and r["familia"] == familia]
    return rs[-1] if rs else None


def ultima_consumida(familia: str, libro: Path = LIBRO) -> int | None:
    hs = [int(r["hasta"]) for r in leer(libro) if r.get("tipo") == "consumida" and (r["familia"] == familia or familia in r.get("relacionadas", []))]
    return max(hs) if hs else None


def problemas(familia: str, desde: int, cid: str, libro: Path = LIBRO, estadistico: str | None = None) -> list:
    e = []
    u = ultima_consumida(familia, libro)
    ra = reuso_autorizado(familia, libro)
    if u is not None and int(desde) <= u and ra and estadistico == "e_proceso" and int(desde) >= int(ra["desde"]):
        u = None                                                                 # reuso autorizado: válido sólo con e-proceso
    elif u is not None and int(desde) <= u and ra:
        e.append(f"la familia {familia} tiene reuso autorizado de sus sesiones miradas sólo con estadistico='e_proceso' (válido ante miradas)")
        u = None
    if u is not None and int(desde) <= u:
        e.append(f"holdout.desde={desde} reusa sesiones ya consumidas por la familia {familia} (o una de la que deriva) hasta {u}; debe empezar después")
    otras = [r["cid"] for r in aperturas_vigentes(familia, libro) if r["cid"] != cid]
    if otras: e.append(f"la familia {familia} ya tiene su única apertura del holdout ({otras[0]})")
    return e


def aperturas_vigentes(familia: str, libro: Path = LIBRO) -> list:
    """Aperturas de la familia que no fueron anuladas DESPUÉS de registrarse (orden del libro)."""
    vig = []
    for r in leer(libro):
        if r.get("familia") != familia: continue
        if r.get("tipo") == "apertura": vig = [v for v in vig if v["cid"] != r["cid"]] + [r]
        elif r.get("tipo") == "anulacion": vig = [v for v in vig if v["cid"] != r["cid"]]
    return vig


def anular_apertura(familia: str, cid: str, motivo: str, n_mirado: int = 0, libro: Path = LIBRO, ahora=None) -> dict:
    """Sólo si no se miró ningún dato del holdout (`n_mirado` = operaciones o sesiones ya contadas con P&L: tiene que ser 0)."""
    if n_mirado: raise ValueError(f"no se anula una apertura con {n_mirado} observaciones del holdout ya miradas")
    if not any(r["cid"] == cid for r in aperturas_vigentes(familia, libro)): raise ValueError(f"{cid}: sin apertura vigente")
    row = dict(tipo="anulacion", familia=familia, cid=cid, motivo=motivo, ts=ahora or time.time())
    with Path(libro).open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


POTENCIA_MIN = 0.8          # E8 (decisión de Nico, 2026-10-26): una lectura de N fijo no se abre sin potencia 0,8
# K27 (Nico, 2026-11-17: «opera demasiado poco»; «mínimo 4 por mes es arbitrario, la idea es que no opere tan poco»): un solo criterio,
# los meses que tarda el forward en decidir = z² / (operaciones por mes × (R/desvío)²), o sea la INFORMACIÓN que junta por mes. Una regla que
# gana mucho por operación pero opera poco y una que opera mucho con poco efecto se miden con la misma vara. Ajustable sólo por Nico.
MESES_MAX_DECISION = 60     # con el efecto completo del desarrollo; SOM 2020+ (20 ops/mes, +0,08 R) necesita 49; Turtles en oro 196


def plan_potencia(tipo: str, efecto: float, sd_op: float, *, n: int | None = None, ops_por_mes: float | None = None,
                  fuente_efecto: str = "", alfa: float = 0.05) -> dict:
    """Plan de potencia que toda apertura declara ANTES de registrarse (K27, 2026-11-17). `tipo`: 'fijo' (una lectura de `n`
    operaciones) o 'e_proceso' (seguimiento secuencial a la frecuencia `ops_por_mes`). `efecto`: R (o unidad de `sd_op`) por operación
    que se espera ver fuera de muestra; si la regla se eligió entre varias, la mitad del de desarrollo (encogimiento por selección).
    Devuelve el plan con `potencia` (fijo) o `meses_para_decidir` (e_proceso) y `problemas` (vacío = se puede abrir)."""
    from edgelab.funnel import escalera as ESC
    import math
    pl = dict(tipo=tipo, efecto=float(efecto), sd_op=float(sd_op), alfa=alfa, fuente_efecto=fuente_efecto, problemas=[])
    if tipo not in ("fijo", "e_proceso"): pl["problemas"].append(f"tipo de plan desconocido: {tipo}")
    if not (efecto > 0 and sd_op > 0):
        pl["problemas"].append("efecto y desvío por operación positivos, declarados antes de abrir"); return pl
    z = ESC._N.inv_cdf(1 - alfa) + ESC._N.inv_cdf(POTENCIA_MIN); pl["n_necesarias"] = int(math.ceil((z * sd_op / efecto) ** 2))
    if tipo == "fijo":
        if not n: pl["problemas"].append("plan 'fijo' sin N de la ventana")
        else:
            pl.update(n=int(n), potencia=round(ESC.potencia(efecto, sd_op / math.sqrt(n), alfa), 3))
            if pl["potencia"] < POTENCIA_MIN:
                pl["problemas"].append(f"potencia {pl['potencia']:.2f} < {POTENCIA_MIN} con N {n} (hacen falta {pl['n_necesarias']}): "
                                       "no se gasta la única apertura (E8); esperar más datos o ir directo al forward secuencial")
    if tipo == "e_proceso":
        if not ops_por_mes or ops_por_mes <= 0: pl["problemas"].append("plan 'e_proceso' sin frecuencia (operaciones por mes)")
        else:
            pl.update(ops_por_mes=float(ops_por_mes), meses_para_decidir=round(pl["n_necesarias"] / ops_por_mes, 1),
                      informacion_mes=round(ops_por_mes * (efecto / sd_op) ** 2, 4))
            if pl["meses_para_decidir"] > MESES_MAX_DECISION:
                pl["problemas"].append(f"tarda {pl['meses_para_decidir']} meses en decidir (> {MESES_MAX_DECISION}): opera demasiado poco "
                                       f"para su efecto (información por mes {pl['informacion_mes']}); subir frecuencia (canasta, más instrumentos, "
                                       "otra temporalidad) antes de abrir (K27)")
    return pl


def plan_desde_ops(R, dias, tipo: str = "e_proceso", n: int | None = None, fraccion_efecto: float = 1.0) -> dict:
    """Plan a partir de las operaciones de desarrollo (R por operación y su día): frecuencia, efecto (× `fraccion_efecto`) y desvío."""
    import numpy as np, pandas as pd
    R = np.asarray(R, float); d = pd.to_datetime(pd.Series(dias).astype(str))
    meses = max(1.0, (d.max() - d.min()).days / 30.44) if len(d) else 1.0
    return plan_potencia(tipo, float(R.mean()) * fraccion_efecto if len(R) else 0.0, float(R.std(ddof=1)) if len(R) > 1 else 0.0,
                         n=n, ops_por_mes=len(R) / meses, fuente_efecto=f"desarrollo × {fraccion_efecto}")


def _exigir_alfa_reservado(familia: str, plan: dict) -> None:
    """K42 (2026-11-18): la potencia de una apertura se calcula al α que la prueba va a usar. Se declaró potencia 0,9 a α 0,05 cuando el
    nivel LORD++ reservado de la familia era 0,0036 (potencia real ≈ 0,5). Si la familia tiene una reserva sin resolver en el libro
    único, el `alfa` del plan no puede ser mayor que su nivel."""
    if plan.get("tipo") != "fijo" or "alfa" not in plan: return
    from edgelab.funnel.libro_lord import LibroLord
    abiertas = [r for r in (LibroLord().estado.get("reservas") or {}).values() if r["familia"] == familia and not r["resuelta"]]
    if abiertas and float(plan["alfa"]) > min(r["nivel"] for r in abiertas) * (1 + 1e-9):
        raise ValueError(f"{familia}: plan de potencia a α {plan['alfa']:.4g}, mayor que el nivel LORD++ reservado "
                         f"{min(r['nivel'] for r in abiertas):.4g}: recalcular con alfa=nivel (K42)")


def registrar_apertura(familia: str, cid: str, desde: int, n_fijo: int, libro: Path = LIBRO, ahora=None, *, plan: dict | None = None) -> dict:
    """Registra la ÚNICA apertura de la familia. Exige `plan` de `plan_potencia` sin problemas (K27): ninguna ruta, ad hoc o del embudo,
    abre sin potencia."""
    if any(r["cid"] == cid for r in aperturas_vigentes(familia, libro)):
        return {}
    if plan is None: raise ValueError(f"{cid}: apertura sin plan de potencia (holdout_ventanas.plan_potencia, K27)")
    if plan.get("problemas"): raise ValueError(f"{cid}: no se abre: " + "; ".join(plan["problemas"]))
    if Path(libro).resolve() == LIBRO.resolve(): _exigir_alfa_reservado(familia, plan)
    row = dict(tipo="apertura", familia=familia, cid=cid, desde=int(desde), n_fijo=int(n_fijo), ts=ahora or time.time(),
               plan={k: v for k, v in plan.items() if k != "problemas"})
    Path(libro).parent.mkdir(parents=True, exist_ok=True)
    with Path(libro).open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def sincronizar(origen: Path = LIBRO, destino: Path | None = None) -> int:
    """Agrega a `destino` las filas de `origen` que le faltan (unión append-only; no borra ni reordena). En el Debian el embudo
    escribe sus aperturas en el clon de ESTADO (que sync_state.sh sube a `autopilot/state`), no en el clon de código fijado: antes
    las escribía en `docs/` del clon de código, donde no se publicaban y bloqueaban `update.sh`. Este paso trae al libro del
    estado las ventanas consumidas que se registran en el repo. Devuelve cuántas filas agregó."""
    if destino is None or Path(destino).resolve() == Path(origen).resolve(): return 0
    tiene = {json.dumps(r, sort_keys=True) for r in leer(destino)}
    nuevas = [r for r in leer(origen) if json.dumps(r, sort_keys=True) not in tiene]
    if nuevas:
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
        with Path(destino).open("a", encoding="utf-8", newline="\n") as f:
            for r in nuevas: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(nuevas)
