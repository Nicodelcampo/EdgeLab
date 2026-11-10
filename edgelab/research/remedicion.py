"""Re-medición (2026-11-10, pedido de Nico): qué corridas anteriores darían otro resultado con la forma de medir de hoy.

Cada vez que EdgeLab cambia CÓMO mide (R en vez de puntos, bruto además de neto, stop mínimo por fricción, control que comparte la
condición, estratos sin empates, banco de eventos…), el cambio se asienta en `docs/research/CAMBIOS_DE_MEDICION.jsonl` con su fecha,
por qué cambiaría los resultados, cómo re-medir y a qué familias afecta. Este módulo cruza ese registro con el índice de familias
(`tools/familias.py::tabla`) y con el código, y produce:
  - candidatas a re-medir (familia × cambios que la alcanzan, con prioridad);
  - estructuras de código que todavía usan la medición vieja (`patron_codigo`).
Es una lista de CANDIDATAS: el agente verifica cada una contra su carpeta antes de relanzar, y una re-medición es una prueba nueva
(cuenta en el registro global y declara linaje a la familia original). Nunca se re-mide sobre datos ya usados para elegir.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAMBIOS = ROOT / "docs/research/CAMBIOS_DE_MEDICION.jsonl"
FECHA_DESCONOCIDA = "2026-10-01"                 # familias sin fecha de registro: anteriores al libro de linajes
PESO_DESENLACE = {"SIN_CANDIDATAS": 3.0, "PISTAS_VIVAS": 2.5, "REFUTADA": 1.5, "SIN_POTENCIA": 2.0}


def cargar(path: Path = CAMBIOS) -> list:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def alcanza(c: dict, f: dict) -> bool:
    """¿El cambio `c` alcanza a la familia `f` (fila de tools/familias.py::tabla)?"""
    a = c.get("afecta") or {}
    if not a: return False                                                     # cambios sólo de código (patron_codigo)
    reg = f.get("registrada") or FECHA_DESCONOCIDA
    if a.get("registrada_antes") and not reg < a["registrada_antes"]: return False
    if a.get("con_pruebas") and not f.get("pruebas"): return False
    if a.get("con_desenlace") and not f.get("desenlaces"): return False
    if a.get("excluir_sufijo") and f["familia"].endswith(a["excluir_sufijo"]): return False
    if a.get("nombre_regex") and not re.search(a["nombre_regex"], f["familia"]): return False
    if a.get("desenlace_regex") and not any(re.search(a["desenlace_regex"], d) for d in f.get("desenlaces", [])): return False
    if a.get("excluir_desenlace_regex") and any(re.search(a["excluir_desenlace_regex"], d) for d in f.get("desenlaces", [])): return False
    if a.get("excluir_carpeta_regex") and any(re.search(a["excluir_carpeta_regex"], c) for c in f.get("carpetas", [])): return False
    return True


def candidatas(familias: list, cambios: list) -> list:
    """Familias alcanzadas por al menos un cambio, con prioridad = cambios que la alcanzan × peso de su desenlace × (1 + factores)."""
    out = []
    for f in familias:
        cs = [c for c in cambios if alcanza(c, f)]
        if not cs: continue
        des = " ".join(f.get("desenlaces", []))
        peso = max([v for k, v in PESO_DESENLACE.items() if k in des] or [1.0])
        nofac = sum("NO_REPETIR" in x for x in f.get("factores", []))
        out.append(dict(familia=f["familia"], registrada=f.get("registrada") or "", desenlaces=f.get("desenlaces", []),
                        carpetas=f.get("carpetas", []), cambios=[c["id"] for c in cs], factores=f.get("factores", []),
                        prioridad=round(len(cs) * peso * (1 + 0.5 * nofac), 2)))
    return sorted(out, key=lambda r: (-r["prioridad"], r["familia"]))


def patrones_codigo(cambios: list, root: Path = ROOT, carpetas=("edgelab/research", "tools")) -> list:
    """Archivos que todavía contienen el patrón de una medición vieja: candidatos a mejorar la estructura."""
    out = []
    for c in cambios:
        pat = c.get("patron_codigo")
        if not pat: continue
        rx = re.compile(pat)
        for d in carpetas:
            for f in sorted((root / d).rglob("*.py")):
                if "__pycache__" in f.parts or "kernel_" in f.name: continue
                for i, l in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if rx.search(l): out.append(dict(cambio=c["id"], archivo=str(f.relative_to(root)), linea=i, texto=l.strip()[:140]))
    return out


def markdown(cands: list, cambios: list, codigo: list, tope: int = 40) -> str:
    L = ["# Re-mediciones candidatas — qué corridas darían otro resultado con la medición de hoy", "",
         "Estado: VIGENTE (GENERADO con `python tools/remediciones.py --write`; no editar a mano). Registro de cambios:",
         "`docs/research/CAMBIOS_DE_MEDICION.jsonl` (un cambio de medición nuevo se asienta ahí en el mismo commit que lo introduce).", "",
         "Son CANDIDATAS: antes de relanzar, verificar en la carpeta de la familia que el cambio de verdad la alcanza. Una re-medición",
         "es una prueba nueva (registro global + linaje a la familia original) y nunca usa datos ya usados para elegir.", "",
         "## Cambios de medición", "", "| Id | Fecha | Qué cambió | Por qué daría otro resultado | Cómo re-medir |", "|---|---|---|---|---|"]
    L += [f"| `{c['id']}` | {c['fecha']} | {c['que_cambio']} | {c['por_que_distinto']} | {c['como_remedir']} |" for c in cambios]
    L += ["", f"## Familias candidatas ({len(cands)}; se listan las {min(tope, len(cands))} de mayor prioridad)", "",
          "| Prioridad | Familia | Registrada | Cambios que la alcanzan | Último desenlace | Carpetas |", "|---|---|---|---|---|---|"]
    for r in cands[:tope]:
        des = "; ".join(sorted(set(r["desenlaces"]))[:2]) or "—"
        L.append(f"| {r['prioridad']} | `{r['familia']}` | {r['registrada'] or '—'} | {', '.join(r['cambios'])} | {des} | "
                 f"{', '.join('`' + c + '`' for c in r['carpetas'][:2]) or '—'} |")
    L += ["", f"## Código con la medición vieja ({len(codigo)})", ""]
    L += [f"- `{x['archivo']}:{x['linea']}` ({x['cambio']}): `{x['texto']}`" for x in codigo] or ["Ninguno."]
    return "\n".join(L) + "\n"
