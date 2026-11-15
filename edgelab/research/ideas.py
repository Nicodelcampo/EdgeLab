"""Banco de ideas multi-fuente (2026-11-14, pedido de Nico): EdgeLab, literatura, StrategyQuant X, practicantes y comunidad como
fuentes de ideas para la línea SQX/MT5 y para el agente del Debian. Archivo: docs/research/ideas/BANCO_IDEAS.jsonl (una ficha por
línea); vista: docs/research/ideas/BANCO_IDEAS.md (`python tools/ideas.py --write`).

Reglas: una ficha por MECANISMO (las fuentes se acumulan en `fuentes`, no se duplica la idea); toda ficha declara mecanismo,
justificación económica, cómo podría refutarse y su traducción operable; el prior (alto/medio/bajo/minimo) fija el peso de alfa
(LORD++), no si se prueba. `lote()` elige el próximo lote BALANCEADO: rota clases de mecanismo y de activo, pondera por prior y no
repite lo ya en prueba; `novedad()` del autopilot descarta ideas casi iguales a las existentes o a las NO_REPETIR."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANCO = ROOT / "docs/research/ideas/BANCO_IDEAS.jsonl"
VISTA = ROOT / "docs/research/ideas/BANCO_IDEAS.md"
FUENTES = ("edgelab", "literatura", "sqx", "practicante", "comunidad", "busqueda_libre")
PRIORES = {"alto": 4.0, "medio": 2.0, "bajo": 1.0, "minimo": 0.5}          # peso relativo de alfa (LORD++) y de elección en el lote
CLASES = ("tendencia", "reversion", "estacionalidad", "carry_macro", "evento", "ruptura", "microestructura", "volatilidad", "cartera")
ESTADOS = ("PROPUESTA", "EN_DISENO", "EN_PRUEBA", "PISTA_VIVA", "REFUTADA", "NO_REPETIR")
OBLIGATORIOS = ("id", "titulo", "fuente_tipo", "fuentes", "clase", "mecanismo", "justificacion_economica", "como_refutarla",
                "traduccion", "activos", "horizonte", "prior", "estado")


def leer(p: Path | None = None) -> list:
    p = BANCO if p is None else p
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def validar(f: dict) -> list:
    e = [f"falta {k}" for k in OBLIGATORIOS if not f.get(k)]
    if f.get("fuente_tipo") not in FUENTES: e.append(f"fuente_tipo ∉ {FUENTES}")
    if f.get("prior") not in PRIORES: e.append(f"prior ∉ {tuple(PRIORES)}")
    if f.get("clase") not in CLASES: e.append(f"clase ∉ {CLASES}")
    if f.get("estado") not in ESTADOS: e.append(f"estado ∉ {ESTADOS}")
    return e


def agregar(f: dict, p: Path | None = None, umbral: float = 0.6) -> dict:
    p = BANCO if p is None else p
    """Agrega una ficha si es válida y nueva; si el mecanismo ya existe (Jaccard ≥ umbral) devuelve la parecida sin agregar."""
    from edgelab.autopilot.contexto import novedad
    if (e := validar(f)): raise ValueError("; ".join(e))
    B = leer(p)
    if any(x["id"] == f["id"] for x in B): raise ValueError(f"id repetido: {f['id']}")
    nueva, parecida, sim = novedad(dict(familia=f["titulo"], mecanismo=f["mecanismo"]), [x["titulo"] + " " + x["mecanismo"] for x in B])
    if not nueva: return dict(agregada=False, parecida_a=parecida, similitud=sim)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh: fh.write(json.dumps(f, ensure_ascii=False) + "\n")
    return dict(agregada=True)


def balance(B: list | None = None) -> dict:
    B = leer() if B is None else B
    return {k: dict(Counter(x[k] if isinstance(x[k], str) else "/".join(x[k]) for x in B)) for k in ("fuente_tipo", "clase", "prior", "estado", "horizonte")}


def lote(n: int = 5, B: list | None = None) -> list:
    """Próximo lote balanceado: sólo PROPUESTA; ronda por clase de mecanismo (la menos representada entre lo ya en prueba primero),
    dentro de cada clase la de mayor prior; nunca dos de la misma clase hasta agotar las clases."""
    B = leer() if B is None else B
    usadas = Counter(x["clase"] for x in B if x["estado"] in ("EN_DISENO", "EN_PRUEBA", "PISTA_VIVA"))
    cand = sorted((x for x in B if x["estado"] == "PROPUESTA"), key=lambda x: -PRIORES[x["prior"]])
    por_clase = {}
    for x in cand: por_clase.setdefault(x["clase"], []).append(x)
    out = []
    while len(out) < n and any(por_clase.values()):
        for c in sorted(por_clase, key=lambda c: (usadas[c], -PRIORES[por_clase[c][0]["prior"]] if por_clase[c] else 0)):
            if por_clase[c] and len(out) < n: out.append(por_clase[c].pop(0)); usadas[c] += 1
    return out


def markdown(B: list | None = None) -> str:
    B = leer() if B is None else B
    L = ["# Banco de ideas (generado por `python tools/ideas.py --write`; no editar a mano)", "",
         "Estado: VIGENTE. Fuente: `docs/research/ideas/BANCO_IDEAS.jsonl` (`edgelab/research/ideas.py`).", "",
         f"Balance: `{json.dumps(balance(B), ensure_ascii=False)}`", ""]
    for x in sorted(B, key=lambda x: (x["clase"], -PRIORES[x["prior"]], x["id"])):
        L += [f"## {x['id']} — {x['titulo']}", f"- Clase: {x['clase']} · fuente: {x['fuente_tipo']} · prior: {x['prior']} · estado: {x['estado']}"
              f" · horizonte: {x['horizonte']} · activos: {', '.join(x['activos'])}",
              f"- Mecanismo: {x['mecanismo']}", f"- Justificación económica: {x['justificacion_economica']}",
              f"- Cómo podría refutarse: {x['como_refutarla']}", f"- Traducción: {x['traduccion']}",
              f"- Fuentes: {'; '.join(x['fuentes'])}", ""]
    return "\n".join(L)


def resumen_para_agente(n: int = 4) -> dict:
    """Lo que el proponente del Debian recibe cada ciclo: balance y el próximo lote balanceado (títulos y mecanismos, acotado)."""
    B = leer()
    return dict(archivo=str(BANCO.relative_to(ROOT)), balance=balance(B) if B else {},
                proximo_lote=[dict(id=x["id"], titulo=x["titulo"], clase=x["clase"], prior=x["prior"], mecanismo=x["mecanismo"][:220]) for x in lote(n, B)])
