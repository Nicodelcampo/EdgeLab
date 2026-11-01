"""Ciclo diario de la cartera viva: datos nuevos -> seguimiento y retiros -> régimen de mañana -> afinidad -> contratos por cuenta ->
cola de investigación -> plan del día. Corre después del cierre de CME (17:00 ET) y tiene que terminar antes de `plazo_et` (por
defecto 17:45 ET, antes de la apertura asiática). Si algo falla o se pasa del plazo, el plan sale en MODO SEGURO (cero contratos
nuevos en todas las cuentas: quedarse afuera nunca rompe una regla de prop firm) y se escribe una alerta. Urgencia, pero sin operar a
ciegas.
"""
from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from edgelab.cartera import afinidad as AF, asignacion as AS, investigacion as IV, papel as PA, regimen as RG
from edgelab.cartera.ficha import Cartera, Ficha


def regimen_siguiente(diario: pd.DataFrame, cortes: dict) -> tuple:
    """(etiqueta de cada sesión ya cerrada, etiqueta del día siguiente a la última sesión)."""
    d = diario.sort_values("fecha").reset_index(drop=True)
    sig = pd.concat([d, pd.DataFrame(dict(fecha=[int(d.fecha.iloc[-1]) + 1], h=[float("nan")], l=[float("nan")], c=[float("nan")]))])
    r = RG.rasgos_diarios(sig.reset_index(drop=True))
    et = RG.etiquetar(r, cortes)
    return et.iloc[:-1], et.iloc[-1], r.iloc[-1].to_dict()


def _alerta(cfg, texto):
    p = cfg.get("alertas")
    if not p: return
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with Path(p).open("a", encoding="utf-8") as f: f.write(json.dumps(dict(ts=time.time(), alerta="cartera", texto=texto, fuente="cartera_viva"), ensure_ascii=False) + "\n")


def _reglas_firma(cuenta: dict, catalogos: list):
    if not cuenta.get("firma"): return None
    from edgelab.propfirm.rules import load_catalog
    for c in catalogos:
        for r in load_catalog(c):
            if r.firm == cuenta["firma"] and r.plan == cuenta["plan"]: return r
    raise ValueError(f"cuenta {cuenta['id']}: {cuenta['firma']}/{cuenta['plan']} no está en los catálogos")


def altas_pendientes(cart, cfg: dict, repo: Path) -> list:
    """Da de alta en PAPEL las fichas declaradas en `cfg["altas"]` (JSON committeado, `tools/cartera_diaria.py preparar-altas`) que
    la cartera todavía no tiene. Idempotente. Una alta rechazada (sin pre-registro, ventana ya usada, regla retirada) se informa y no
    frena el ciclo: no es motivo de modo seguro."""
    ruta = cfg.get("altas")
    if not ruta: return []
    ruta = Path(ruta) if Path(ruta).is_absolute() else Path(repo) / ruta
    if not ruta.exists(): return [dict(error=f"no existe {ruta}")]
    out = []
    for d in json.loads(ruta.read_text(encoding="utf-8")).get("fichas", []):
        if d["id"] in cart.fichas: continue
        try: out.append(dict(id=cart.alta(Ficha(**d), repo).id, alta=True))
        except ValueError as ex:
            out.append(dict(id=d["id"], alta=False, motivo=str(ex))); _alerta(cfg, f"cartera viva: alta de {d['id']} rechazada: {ex}")
    return out


def correr(cfg: dict, hasta: int, diarios: dict, runner=None, fills: list | None = None, ahora=time.time, repo: Path = Path(".")) -> dict:
    t0 = ahora(); pasos = {}; seguro = None
    cart = Cartera(Path(cfg["cartera"]), reglas=cfg.get("reglas"), libro_ventanas=cfg.get("libro_ventanas"))
    plan = dict(schema="edgelab_cartera_plan_v1", hasta=int(hasta), generado=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    try:
        pasos["altas"] = altas_pendientes(cart, cfg, repo)
        antes = {f.id for f in cart.activas()}
        pasos["seguimiento"] = PA.actualizar(cart, runner, hasta, cfg.get("calentamiento_dias", 45)) if runner is not None else []
        retiros = [dict(id=k, motivo=cart.fichas[k].motivo) for k in antes if cart.fichas[k].estado == "RETIRADA"]
        reg_ses, reg_man, rasgos = {}, {}, {}
        for inst, d in diarios.items():
            if inst not in (cfg.get("cortes_regimen") or {}): continue
            s, m, x = regimen_siguiente(d, cfg["cortes_regimen"][inst]); reg_ses[inst], reg_man[inst], rasgos[inst] = s, m, x
        mult = {}
        for f in cart.activas():
            ops = pd.DataFrame([*f.ops_desarrollo, *f.ops], columns=["ses", "neto"]) if (f.ops_desarrollo or f.ops) else pd.DataFrame(columns=["ses", "neto"])
            mult[f.id] = AF.multiplicador(ops, reg_ses.get(f.instrumento, pd.Series(dtype=object)), reg_man.get(f.instrumento))
        cuentas = [AS.asignar(c, cart.activas(), mult, _reglas_firma(c, cfg.get("catalogos_propfirm", [])), cfg.get("peso_max", 0.25),
                              cfg.get("peso_max_instrumento", 0.5)) for c in cfg.get("cuentas", [])]
        cola = IV.cola(list(cart.fichas.values()), reg_man, mult, retiros, IV.estados_embudo(repo, cfg.get("estados_extra")),
                       cfg.get("objetivo_por_instrumento", 3), tuple(cfg.get("instrumentos", ("NQ", "ES", "YM", "GC"))))
        brecha = None
        if fills:
            papel = {(f.id, int(s)): x for f in cart.fichas.values() for s, x in f.ops}
            g = [(r["estrategia"], r["neto_pts"] - papel[(r["estrategia"], int(r["ses"]))]) for r in fills if (r["estrategia"], int(r["ses"])) in papel]
            brecha = pd.DataFrame(g, columns=["estrategia", "dif"]).groupby("estrategia").dif.agg(["count", "mean"]).reset_index().to_dict("records") if g else []
        plan.update(altas=pasos["altas"], regimen_manana=reg_man, rasgos=rasgos, multiplicadores=mult, retiros_hoy=retiros, cuentas=cuentas, cola_investigacion=cola,
                    ejecucion_vs_papel=brecha, cartera=[dict(id=f.id, familia=f.familia, instrumento=f.instrumento, nivel=f.nivel, estado=f.estado,
                                                              n_forward=len(f.ops), neto_forward=round(sum(x for _, x in f.ops), 2),
                                                              motivo=f.motivo) for f in cart.fichas.values()])
    except Exception as ex:                                                          # modo seguro: nadie opera a ciegas
        seguro = f"{type(ex).__name__}: {ex}"; plan["traza"] = traceback.format_exc()[-3000:]
    dur = ahora() - t0
    if seguro is None and dur > cfg.get("plazo_s", 2700): seguro = f"ciclo de {dur:.0f} s supera el plazo de {cfg.get('plazo_s', 2700)} s"
    if seguro:
        plan["modo_seguro"] = seguro
        for c in plan.get("cuentas", []):
            for p in c["posiciones"]: p["contratos"] = 0
            c["operar"] = False
        _alerta(cfg, f"cartera viva en MODO SEGURO ({hasta}): {seguro}")
    plan["duracion_s"] = round(dur, 1)
    if any(a["prioridad"] == "P0" for a in plan.get("cola_investigacion", [])):
        _alerta(cfg, f"cartera viva ({hasta}): {sum(a['prioridad'] == 'P0' for a in plan['cola_investigacion'])} acciones P0 para hoy")
    out = Path(cfg["salida"]) / str(hasta); out.mkdir(parents=True, exist_ok=True)
    (out / "PLAN.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "PLAN.md").write_text(resumen_md(plan), encoding="utf-8")
    (Path(cfg["salida"]) / "PLAN_ACTUAL.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return plan


def resumen_md(plan: dict) -> str:
    L = [f"# Plan de la cartera viva — sesión siguiente a {plan['hasta']}", "",
         f"Estado: VIGENTE (generado {plan['generado']}, {plan.get('duracion_s')} s)." + (f" **MODO SEGURO: {plan['modo_seguro']}**" if plan.get("modo_seguro") else ""), ""]
    L += ["## Régimen de mañana", ""] + [f"- {k}: {v}" for k, v in (plan.get("regimen_manana") or {}).items()] + [""]
    L += ["## Cuentas", ""]
    for c in plan.get("cuentas", []):
        L.append(f"- **{c['cuenta']}** ({c['tipo']}): " + ("no opera — " + c.get("motivo", "") if not c["operar"] else
                 f"presupuesto {c['presupuesto_usd']} USD, asignado {c['riesgo_asignado_usd']} USD, stop del día {c['stop_dia_usd']} USD"))
        for p in c["posiciones"]:
            if p["contratos"]: L.append(f"  - {p['estrategia']}: {p['contratos']} {p['contrato']} (peso {p['peso']}, régimen ×{p['multiplicador_regimen']})")
    L += ["", "## Retiros de hoy", ""] + ([f"- {r['id']}: {r['motivo']}" for r in plan.get("retiros_hoy", [])] or ["- ninguno"])
    L += ["", "## Cola de investigación", ""] + ([f"- {a['prioridad']} ({a['plazo']}) {a['accion']} {a['objetivo']}: {a.get('motivo', '')}"
                                                  for a in plan.get("cola_investigacion", [])] or ["- vacía"])
    return "\n".join(L) + "\n"


def sesion_cerrada(ahora_utc: datetime | None = None) -> int:
    """Última sesión CME cerrada (la sesión de fecha D cierra a las 17:00 ET de D; se usa 21:00 UTC como corte conservador)."""
    t = ahora_utc or datetime.now(timezone.utc)
    d = t.date() if t.hour >= 21 else t.date() - timedelta(days=1)
    while d.weekday() >= 5: d -= timedelta(days=1)
    return d.year * 10000 + d.month * 100 + d.day
