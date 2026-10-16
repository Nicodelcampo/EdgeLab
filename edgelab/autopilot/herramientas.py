"""Kit de herramientas del agente (pedido de Nico, 2026-10-16): qué técnicas existen, cuáles tienen paridad probada,
y cuánto rindió cada una. Diseño: docs/autopilot/KIT_DE_HERRAMIENTAS_Y_MEJORA_20261016.md.

Tres estados, fijados en config/autopilot/herramientas.json y no en un prompt:
  verificada  -> hay implementación en el repo y una prueba contra la librería de referencia: sirve para medir.
  propuesta   -> existe como idea o como script ad hoc sin prueba de paridad: sirve para PROPONER, no para medir.
  falta       -> no está en el repo: el agente la pide como mejora de módulo (PROPUESTA; se acepta sólo con tests verdes y revisión de PR).
El proponente recibe el catálogo con su rendimiento; la promoción rechaza candidatas que miden con técnicas sin paridad.
"""
from __future__ import annotations
import json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOGO = ROOT / "config" / "autopilot" / "herramientas.json"
ESTADOS = ("verificada", "propuesta", "falta")


def cargar(path: Path = CATALOGO) -> dict:
    cat = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {t["id"]: t for t in cat["tecnicas"]}
    for t in out.values():
        if t.get("estado", "propuesta") not in ESTADOS: raise ValueError(f"{t['id']}: estado inválido {t.get('estado')}")
    return out


def faltantes(c, cat: dict | None = None) -> list:
    """Chequeo mecánico: toda técnica que la candidata declara en cfg['tecnicas'] existe y está verificada."""
    cat = cat or cargar(); out = []
    for t in (getattr(c, "cfg", {}) or {}).get("tecnicas", []):
        if t not in cat: out.append(f"técnica desconocida: {t}; pedirla como mejora de módulo")
        elif cat[t].get("estado", "propuesta") != "verificada": out.append(f"técnica {t} está '{cat[t].get('estado', 'propuesta')}': sin paridad no se mide con ella")
    return out


def pedir_mejoras(c, registro, cat: dict | None = None) -> list:
    """Cada técnica que falta o no tiene paridad se convierte en una propuesta de mejora de módulo (ámbito 'modulo': nunca se aplica sola)."""
    cat = cat or cargar(); out = []
    for t in (getattr(c, "cfg", {}) or {}).get("tecnicas", []):
        if cat.get(t, {}).get("estado", "falta") != "verificada":
            out.append(registro.proponer("modulo", f"implementar o verificar la técnica {t}", f"la pidió la candidata {c.cid}: {cat.get(t, {}).get('verificar_contra', 'sin referencia')}"))
    return out


def registrar_uso(path: Path, tecnica: str, run_id: str, resultado: str) -> None:
    """resultado: lanzada | hit | nulo | fallo. Append-only; lo cierra quien analiza la corrida."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(ts=time.time(), tecnica=tecnica, run_id=run_id, resultado=resultado), ensure_ascii=False) + "\n")


def rendimiento(path: Path | None) -> dict:
    """{tecnica: {usos, hits, nulos, fallos}} a partir del ledger. Sin ledger, vacío."""
    out: dict = {}
    if not path or not Path(path).exists(): return out
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        r = json.loads(l); d = out.setdefault(r["tecnica"], dict(usos=0, hits=0, nulos=0, fallos=0))
        if r["resultado"] == "lanzada": d["usos"] += 1
        elif r["resultado"] in ("hit", "nulo", "fallo"): d[r["resultado"] + "s"] += 1
    return out


def para_contexto(cat: dict | None = None, ledger: Path | None = None) -> dict:
    """Lo que ve el proponente: id, estado, uso y rendimiento. Determinista (orden del catálogo)."""
    cat = cat or cargar(); r = rendimiento(ledger)
    return dict(regla="proponer con cualquiera; medir sólo con 'verificada'; lo que falta se pide como mejora de módulo",
                tecnicas=[dict(id=k, estado=v.get("estado", "propuesta"), uso=v["uso"], **({"rendimiento": r[k]} if k in r else {})) for k, v in cat.items()])
