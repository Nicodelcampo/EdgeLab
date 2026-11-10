"""Cierre de ciclo: de cada campaña cerrada al registro de factores (pedido de Nico, 2026-11-09).

El embudo deja `META_PENDIENTE.json` al cerrar una campaña. `procesar` llama al rol `meta_analista` (el modelo del arquitecto, ver
config/autopilot/AGENTES.json) con el estado de la campaña y el registro vigente, y asienta lo que devuelve en
`docs/research/FACTORES.jsonl` como PROPUESTO_META (o SIN_FACTOR si no hay nada aprovechable). Nada de esto promueve ni decide: ordena
qué indagar. Si el rol falla o está sin cupo, el pendiente queda para el próximo ciclo.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from edgelab.autopilot.contexto import con_nucleo, redactar
from edgelab.research import factores as F

CAMPANAS = "config/autopilot/grillas/campanas"


def pendientes(raiz_embudo) -> list:
    return sorted(Path(raiz_embudo).glob("*/META_PENDIENTE.json"))


def _resumen(st: dict, tope: int = 30000) -> str:
    """Estado de la campaña sin la spec (ya es pública) ni rutas locales, acotado."""
    s = {k: v for k, v in st.items() if k != "spec"}
    s["historial"] = (s.get("historial") or [])[-12:]
    return redactar(json.dumps(s, ensure_ascii=False, default=float))[:tope]


def _evidencia(cid: str, spec: dict, root: Path) -> list:
    cand = [spec.get("preregistro"), f"{CAMPANAS}/{cid}.json"]
    return [c for c in cand if c and (root / c).exists()][:1]


def procesar(runner, raiz_embudo, *, limite: int = 3, root: Path = F.ROOT, libro: Path = F.LIBRO, hoy: str | None = None) -> list:
    hoy = hoy or time.strftime("%Y-%m-%d"); hechos = []
    for marca in pendientes(raiz_embudo)[:limite]:
        m = json.loads(marca.read_text(encoding="utf-8")); cid = m["cid"]
        f_st = marca.parent / "estado.json"
        st = json.loads(f_st.read_text(encoding="utf-8")) if f_st.exists() else {}
        ev = _evidencia(cid, st.get("spec") or {}, root)
        if not ev: hechos.append(dict(cid=cid, estado="SIN_EVIDENCIA_EN_REPO")); continue      # se reintenta cuando la campaña esté en el repo
        vig = [dict(id=e["id"], estado=e["estado"], factor=e["factor"]) for e in F.cargar(libro)]
        # Método de investigación §8: si la campaña dejó RECOMENDACIONES_*.md (recomendador), van al meta-analista como punto de partida
        dirs = {marca.parent} | ({(root / (st.get("spec") or {}).get("preregistro", "")).parent} if (st.get("spec") or {}).get("preregistro") else set())
        recs = {f.name: redactar(f.read_text(encoding="utf-8"))[:12000] for d in dirs if d.is_dir() for f in sorted(d.glob("RECOMENDACIONES_*.md"))[:3]}
        r = runner.call("meta_analista", con_nucleo("meta_analista", dict(campana=cid, cierre=dict(final=m["final"], motivo=redactar(str(m["motivo"]))),
                                                                          estado_campana=_resumen(st), factores_vigentes=vig, recomendaciones=recs)))
        if r.get("status") not in ("OK", "CACHED"): hechos.append(dict(cid=cid, estado=r.get("status"))); continue
        out = r["output"]; n = 0
        for k, fx in enumerate(out.get("factores") or []):
            try:
                F.registrar(id=f"M-{cid}-{hoy}-{k}", fecha=hoy, estado="PROPUESTO_META", factor=fx["factor"], efecto=f"{fx['efecto_r']} — {fx['evidencia']} (confianza {fx['confianza']})",
                            donde=fx["donde"], evidencia=ev, siguiente=fx["siguiente_indagacion"], origen="meta_analista", libro=libro, root=root); n += 1
            except ValueError: pass                                                           # id repetido: ya estaba asentado
        if not n:
            try: F.registrar(id=f"M-{cid}-{hoy}-sin", fecha=hoy, estado="SIN_FACTOR", factor=f"{cid}: cerrada como {m['final']}", efecto="; ".join(out.get("que_no_repetir") or []) or "sin factor aprovechable",
                             donde=cid, evidencia=ev, siguiente=out.get("prioridad_siguiente") or "—", origen="meta_analista", libro=libro, root=root)
            except ValueError: pass
        marca.unlink(); hechos.append(dict(cid=cid, estado="ASENTADO", factores=n))
    if hechos and libro == F.LIBRO: F.escribir()
    return hechos
