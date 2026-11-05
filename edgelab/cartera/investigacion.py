"""Cola de investigación con sentido de urgencia: qué lanzar HOY para que la cartera siga cubriendo el régimen actual.

La cartera vive de renovar estrategias de régimen: lo que funciona ahora dura un tiempo. La cola se arma cada día con reglas fijas
(nada se decide mirando P&L del holdout), ordenada por prioridad y con plazo:
  P0 hoy      RETIROS del día: reemplazar (relanzar la familia en su instrumento o la siguiente candidata de la misma idea).
  P0 hoy      HUECO DE RÉGIMEN: un instrumento objetivo con menos de `objetivo_por_instrumento` estrategias activas con afinidad > 0
              para el régimen de mañana -> buscar en ese instrumento y régimen.
  P1 24 h     CANDIDATAS FORWARD: familias en PISTAS_VIVAS con réplica a favor (canasta p <= p_forward) que todavía no están en la
              cartera -> pre-registrar la prueba forward de su canasta congelada y darlas de alta en PAPEL (no consume capital).
  P1 24 h     EMBUDO TRABADO: campañas BLOQUEADAS o esperando datos -> destrabar (causa raíz, no reintento mudo).
  P2 semana   CERCA DE PROMOCIÓN: estrategias en PAPEL con e-proceso a mitad de camino -> priorizar su ejecución en demo NT8.
La salida la lee el agente del Debian (directiva 6 de config/autopilot/DIRECTIVAS.md) para decidir qué campañas lanzar.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path


def estados_embudo(repo: Path, extra: list | None = None) -> list:
    out = []
    for f in sorted(glob.glob(str(Path(repo) / "docs/research/**/embudo/*/estado.json"), recursive=True)) + list(extra or []):
        try: st = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception: continue
        sp = st.get("spec") or {}
        can = ((st.get("pistas_replica") or {}).get("canasta") or {})
        out.append(dict(cid=sp.get("cid"), familia=sp.get("familia"), instrumento=sp.get("ejecucion") or sp.get("sensor"), fase=st.get("fase"),
                        p_canasta=can.get("p"), media_canasta=can.get("media"), estado=f))
    return out


def cola(fichas, regimen_manana: dict, multiplicadores: dict, retiros_hoy: list, embudo: list, objetivo_por_instrumento: int = 3,
         instrumentos=("NQ", "ES", "YM", "GC"), p_forward: float = 0.10, mitad_promocion: float = 0.5) -> list:
    acc = []
    for r in retiros_hoy:
        acc.append(dict(prioridad="P0", plazo="hoy", accion="REEMPLAZAR", objetivo=r["id"], motivo=r.get("motivo")))
    en_cartera = {f.familia for f in fichas}
    for inst in instrumentos:
        vivas = [f for f in fichas if f.estado == "ACTIVA" and f.instrumento == inst and multiplicadores.get(f.id, 1.0) > 0]
        if len(vivas) < objetivo_por_instrumento:
            acc.append(dict(prioridad="P0", plazo="hoy", accion="HUECO_DE_REGIMEN", objetivo=inst, regimen=regimen_manana.get(inst),
                            motivo=f"{len(vivas)} de {objetivo_por_instrumento} estrategias activas con afinidad > 0 para el régimen de mañana"))
    for e in embudo:
        if e["fase"] == "PISTAS_VIVAS" and e["p_canasta"] is not None and e["p_canasta"] <= p_forward and (e["media_canasta"] or 0) > 0 \
                and e["familia"] not in en_cartera:
            acc.append(dict(prioridad="P1", plazo="24 h", accion="ALTA_FORWARD", objetivo=e["cid"], familia=e["familia"],
                            motivo=f"réplica de la canasta a favor (p {e['p_canasta']:.3f}): pre-registrar la prueba forward y dar de alta en PAPEL"))
        if e["fase"] == "BLOQUEADA":
            acc.append(dict(prioridad="P1", plazo="24 h", accion="DESTRABAR", objetivo=e["cid"], motivo="campaña BLOQUEADA: causa raíz"))
    for f in fichas:
        if f.estado == "ACTIVA" and f.nivel == "PAPEL" and len(f.ops) >= 10:
            try: st = f.monitor(0.05, 0.10).estado()
            except ValueError: continue
            if st["e_edge"] >= (st["umbral_edge"] ** mitad_promocion):
                acc.append(dict(prioridad="P2", plazo="semana", accion="CERCA_DE_PROMOCION", objetivo=f.id,
                                motivo=f"e {st['e_edge']:.1f} de {st['umbral_edge']:.0f}: preparar su ejecución en demo NT8"))
    orden = {"P0": 0, "P1": 1, "P2": 2}
    return sorted(acc, key=lambda a: orden[a["prioridad"]])
