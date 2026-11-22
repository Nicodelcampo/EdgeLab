"""Snapshot maestro vivo y compacto (`docs/ESTADO_VIVO.md`, <= 150 lineas).

Persiste las anclas, leyes empiricas, bloqueos `NO_REPETIR`, pistas vivas y
estado de holdout desde las fuentes canonicas del repo en un resumen determinista
que cualquier sesion o rol del autopilot carga completo sin exceder su ventana.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from edgelab import holdout as HO
from edgelab.research import factores as FA
from edgelab.research import holdout_ventanas as HV
from edgelab.research.preflight import north_star_sha256

ROOT = Path(__file__).resolve().parents[2]
SALIDA = ROOT / "docs" / "ESTADO_VIVO.md"
MAX_LINEAS = 150
MAX_CHARS = 7000


def _leer_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _acortar(texto: str, max_len: int) -> str:
    limpio = " ".join(str(texto or "").split())
    return limpio if len(limpio) <= max_len else limpio[: max_len - 1].rstrip() + "…"


def _fecha_determinista(factores: list[dict[str, Any]], ventanas: list[dict[str, Any]]) -> str:
    fechas = [str(f.get("fecha", ""))[:10] for f in factores if f.get("fecha")]
    fechas += [str(v.get("registrada", ""))[:10] for v in ventanas if v.get("registrada")]
    fechas = [f for f in fechas if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f)]
    return max(fechas) if fechas else "2026-11-21"


def _version_lectura_previa(root: Path) -> str:
    p = root / "docs" / "research" / "LEER_ANTES_DE_CADA_CORRIDA.md"
    if not p.exists():
        return "?"
    m = re.search(r"\((v\d+),\s*(\d{4}-\d{2}-\d{2})", p.read_text(encoding="utf-8", errors="ignore")[:500])
    return f"{m.group(1)} ({m.group(2)})" if m else "vigente"


def _edges_promovidos_linea(root: Path) -> str:
    p = root / "EDGES_DISCOVERED.md"
    if not p.exists():
        return "0 (archivo ausente)"
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines()[:15]:
        if "estado actual:" in line.lower():
            return line.split(":", 1)[-1].strip()
    return "0 promovidos"


def _resumen_canastas(root: Path) -> list[str]:
    p = root / "docs" / "cartera" / "CANASTAS_VIGENTES.md"
    if not p.exists():
        return []
    heads = [l[3:].strip() for l in p.read_text(encoding="utf-8", errors="ignore").splitlines() if l.startswith("## ")]
    return [h for h in heads if not h.startswith(("Cómo", "En una", "Lo que"))]


def _invalidaciones_hipocampo(root: Path) -> list[str]:
    hdir = root / "artifacts" / "hippocampus"
    if not hdir.is_dir():
        return []
    out: list[str] = []
    for f in sorted(hdir.glob("*.jsonl")):
        for row in _leer_jsonl(f):
            st = str(row.get("status", "")).upper()
            if "INVALID" in st or "BLOCKED" in st:
                out.append(f"{f.stem}:{row.get('id', row.get('claim_id', '?'))}")
    return out


def recopilar_estado(root: Path | None = None) -> dict[str, Any]:
    """Recopila desde disco el estado canonico para generar `docs/ESTADO_VIVO.md`."""
    base = ROOT if root is None else Path(root)
    factores = FA.cargar(base / "docs" / "research" / "FACTORES.jsonl")
    pistas_vivas = sorted(
        [f for f in factores if f.get("estado") == "PISTA_VIVA"],
        key=lambda x: (x.get("fecha", ""), x.get("id", "")),
        reverse=True,
    )
    palancas = sorted(
        [f for f in factores if f.get("estado") == "PALANCA_DE_DISENO"],
        key=lambda x: (x.get("fecha", ""), x.get("id", "")),
        reverse=True,
    )
    no_repetir = sorted(
        [f for f in factores if f.get("estado") == "NO_REPETIR"],
        key=lambda x: (x.get("fecha", ""), x.get("id", "")),
        reverse=True,
    )
    trials = _leer_jsonl(base / "docs" / "research" / "TRIAL_REGISTRY_GLOBAL.jsonl")
    ventanas = HV.leer(base / "docs" / "research" / "HOLDOUT_VENTANAS.jsonl")
    consumidas: dict[str, int] = {}
    aperturas: list[str] = []
    anuladas: set[str] = set()
    for row in ventanas:
        tipo = row.get("tipo")
        if tipo == "consumida":
            fam = str(row.get("familia", "?"))
            consumidas[fam] = max(consumidas.get(fam, 0), int(row.get("hasta", 0)))
        elif tipo == "apertura":
            aperturas.append(f"{row.get('familia')}:{row.get('cid')}")
        elif tipo == "anulacion":
            anuladas.add(f"{row.get('familia')}:{row.get('cid')}")
    aperturas_activas = [a for a in aperturas if a not in anuladas]
    return {
        "fecha": _fecha_determinista(factores, ventanas),
        "north_star_sha256": north_star_sha256(base),
        "holdout_a4": f"{HO.HOLDOUT_PRIMERA_SESION} ({HO.HOLDOUT_PRIMERA_SESION_INT})",
        "holdout_a5": f"{HO.A5_REPARTO} (semilla {HO.A5_SEMILLA})",
        "lectura_previa_ver": _version_lectura_previa(base),
        "edges_estado": _edges_promovidos_linea(base),
        "trials_campanias": len({r.get("campaign_id") for r in trials}),
        "trials_totales": int(sum(int(r.get("n_trials", 0)) for r in trials)),
        "pistas_vivas": pistas_vivas,
        "palancas": palancas,
        "no_repetir": no_repetir,
        "canastas": _resumen_canastas(base),
        "consumidas": sorted(consumidas.items()),
        "aperturas_activas": aperturas_activas,
        "invalidaciones_hipocampo": _invalidaciones_hipocampo(base),
    }


def renderizar_estado_vivo(root: Path | None = None) -> str:
    """Renderiza `docs/ESTADO_VIVO.md` garantizando determinismo, <= 150 lineas y <= 7000 caracteres."""
    base = ROOT if root is None else Path(root)
    st = recopilar_estado(base)
    fijo_top = [
        "# Estado vivo de EdgeLab (snapshot maestro de contexto)",
        "",
        "Estado: VIGENTE",
        f"Fecha: {st['fecha']}",
        "Fuente: generado por `python tools/contexto_vivo.py --write` (no editar a mano).",
        "",
        "## 1. Anclas e Invariantes (fail-closed)",
        f"- North Star SHA-256: `{st['north_star_sha256']}`",
        f"- Holdout A4/A5: frontera `{st['holdout_a4']}` (`edgelab/holdout.py`); A5 `7 DESC / 2 REP / 3 HOLDOUT`",
        f"- Indice obligatorio: `docs/research/LEER_ANTES_DE_CADA_CORRIDA.md` {st['lectura_previa_ver']}",
        f"- Contador global: `{st['trials_campanias']}` campanas / `{st['trials_totales']:,}` pruebas registradas",
        f"- Edges promovidos: `{st['edges_estado']}` (`EDGES_DISCOVERED.md`)",
        "",
        "## 2. Guardas y Leyes Empiricas Activas",
        "- Costos canonicos unicos: `edgelab/costos.py` (`config/costos/costos_canonicos.json`); prohibido tablas ad-hoc",
        "- Medicion: unidad R sobre stop inicial (bruto+neto, mini+micro); causalidad por prefijo verificada",
        "- Friccion relativa: no elegir micro-edges donde friccion/R > 0.08; stop amplio frente a friccion",
        "- M1 (K40/K43): stop al nivel salvo hueco; toda familia M1 calibra contra ticks por `a5.calibrar_por_sesion`",
        "- Cadena unica: `tools/tablas.py` / `edgelab/research/ejecucion.py`; K27 potencia>=0.8; K51 contado antes; K55/K56 grilla",
        "- Memoria activa (`edgelab/research/memoria_activa.py`): proponer algo en NO_REPETIR exige `Cambio respecto a falla previa:`",
        "- Puertas de salida: `puerta_kernel.py` (pre-push Kaggle AST/holdout/sintetico) y `tools/puerta_corrida.py`",
        "",
        "## 3. Pistas Vivas y Canastas en Papel",
        f"- Pistas vivas (`PISTA_VIVA`): {len(st['pistas_vivas'])} | Palancas (`PALANCA_DE_DISENO`): {len(st['palancas'])}",
    ]
    for pv in st["pistas_vivas"][:6]:
        fijo_top.append(f"  - `{pv['id']}` ({pv['fecha']}): {_acortar(pv['factor'], 92)}")
    if st["canastas"]:
        fijo_top.append("- Canastas papel: " + " | ".join(_acortar(c, 55) for c in st["canastas"][:4]))

    fijo_bot = [
        "",
        "## 5. Holdout Consumido y Aperturas",
        "- Familias con sesiones miradas: "
        + (", ".join(f"`{f}`<={h}" for f, h in st["consumidas"][:10]) or "ninguna")
        + (f" (+{len(st['consumidas']) - 10} mas)" if len(st["consumidas"]) > 10 else ""),
        "- Aperturas confirmatorias activas: "
        + (f"{len(st['aperturas_activas'])} (" + ", ".join(st["aperturas_activas"][:5]) + ")" if st["aperturas_activas"] else "ninguna"),
        "",
        "## 6. Arranque y Cierre Obligatorios (4 comandos)",
        "1. `python tools/estado.py`  2. `python tools/antecedentes.py \"<idea>\" --familia <FAM>`",
        "3. `python tools/puerta_corrida.py --prereg <PREREG.md> --modulo <mod> --exigir-contada`  4. `python tools/cierre.py`",
    ]

    inv_lineas = []
    if st["invalidaciones_hipocampo"]:
        inv_lineas.append("- Invalidaciones hipocampo: " + ", ".join(st["invalidaciones_hipocampo"][:8]))

    nr_header = [
        "",
        f"## 4. Bloqueado / NO_REPETIR ({len(st['no_repetir'])} vigentes en FACTORES.jsonl)",
        *inv_lineas,
    ]
    presup_lineas = MAX_LINEAS - len(fijo_top) - len(fijo_bot) - len(nr_header) - 2
    nr_lines: list[str] = []
    for item in st["no_repetir"]:
        if len(nr_lines) < max(0, presup_lineas - 1):
            nr_lines.append(f"- `{item['id']}` ({item['fecha']}): {_acortar(item['factor'], 78)}")
        else:
            break
    restantes = [x["id"] for x in st["no_repetir"][len(nr_lines) :]]
    if restantes:
        res_line = "- Otros IDs NO_REPETIR: " + ", ".join(f"`{i}`" for i in restantes)
        nr_lines.append(_acortar(res_line, 260))

    lines = fijo_top + nr_header + nr_lines + fijo_bot
    # Ajuste fino si excede MAX_CHARS o MAX_LINEAS manteniendo integridad de secciones 1..6
    while (len(lines) > MAX_LINEAS or len("\n".join(lines) + "\n") > MAX_CHARS) and len(nr_lines) > 1:
        removido = st["no_repetir"][len(nr_lines) - 1]["id"] if nr_lines[-1].startswith("- `F-") else None
        nr_lines.pop()
        if not nr_lines[-1].startswith("- Resumen"):
            resto = len(st["no_repetir"]) - len(nr_lines)
            nr_lines.append(f"- Mas bloqueos en `docs/research/FACTORES.jsonl`: {resto} entradas `NO_REPETIR` adicionales" + (f" (ej. `{removido}`)" if removido else ""))
        lines = fijo_top + nr_header + nr_lines + fijo_bot
        if nr_lines[-1].startswith("- Mas bloqueos") and len(nr_lines) >= 2:
            if len(lines) > MAX_LINEAS or len("\n".join(lines) + "\n") > MAX_CHARS:
                nr_lines.pop(-2)
                resto = len(st["no_repetir"]) - (len(nr_lines) - 1)
                nr_lines[-1] = f"- Ver lista completa `NO_REPETIR` ({len(st['no_repetir'])}) en `docs/research/FACTORES.jsonl`"
                lines = fijo_top + nr_header + nr_lines + fijo_bot
    return "\n".join(lines[:MAX_LINEAS]) + "\n"


def escribir_estado_vivo(root: Path | None = None, out_path: Path | None = None) -> Path:
    base = ROOT if root is None else Path(root)
    dest = out_path or (base / "docs" / "ESTADO_VIVO.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(renderizar_estado_vivo(base), encoding="utf-8", newline="\n")
    return dest


def verificar_estado_vivo(root: Path | None = None, out_path: Path | None = None) -> list[str]:
    """Devuelve lista de errores (vacia = `docs/ESTADO_VIVO.md` vigente y acotado)."""
    base = ROOT if root is None else Path(root)
    dest = out_path or (base / "docs" / "ESTADO_VIVO.md")
    if not dest.exists():
        return [f"falta {dest.relative_to(base).as_posix()}: correr python tools/contexto_vivo.py --write"]
    actual = dest.read_text(encoding="utf-8").replace("\r\n", "\n")
    esperado = renderizar_estado_vivo(base)
    errs: list[str] = []
    n_lineas = len(actual.splitlines())
    if n_lineas > MAX_LINEAS:
        errs.append(f"{dest.name} tiene {n_lineas} lineas (> {MAX_LINEAS})")
    if len(actual) > MAX_CHARS:
        errs.append(f"{dest.name} tiene {len(actual)} chars (> {MAX_CHARS})")
    if actual != esperado:
        errs.append(f"{dest.name} desactualizado: correr python tools/contexto_vivo.py --write")
    return errs
