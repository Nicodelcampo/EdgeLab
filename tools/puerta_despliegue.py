"""Puerta de despliegue: ¿se puede habilitar el bot de una cuenta prop/real tal como está configurado?

Equivalente de `tools/puerta_corrida.py` para producción. Lee `config/cuentas_activas.json` y BLOQUEA (sale 1) si:
  1. riesgo  : el peor caso abierto (sleeves simultáneos x pérdida máxima por sleeve) o el límite diario del bot
               superan su fracción del colchón restante al piso, o el piso no está verificado en una cuenta real;
  2. ejecución: no hay auditoría de ejecución en demo reciente para el instrumento, con n suficiente y fricción
               implícita dentro de la canónica (`edgelab/costos.py`, nunca una tabla local);
  3. reglas  : falta el cierre forzado antes del flat de la firma o la política de noticias;
  4. deriva  : el archivo instalado en la plataforma difiere del repo (`tools/deriva_bots.py`).
La puerta no habilita ni opera nada: dice si se puede y por qué no. Activar con dinero real lo decide Nico.

  python tools/puerta_despliegue.py --cuenta LFE02575951920002
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab import costos  # noqa: E402

FUENTE = ROOT / "config" / "cuentas_activas.json"
LIM = {"frac_peor_caso": 0.50,      # peor caso abierto <= 50 % del colchón
       "frac_diario": 0.50,         # límite diario del bot <= 50 % del colchón
       "n_min_auditoria": 10,       # idas y vueltas mínimas en la auditoría de demo
       "minutos_antes_flat": 5}     # cierre forzado al menos 5 min antes del flat de la firma


def _min(hhmm: int) -> int:
    return hhmm // 100 * 60 + hhmm % 100


def evaluar(c: dict, cuenta_id: str, hoy: date, deriva=None) -> tuple[list[str], list[str]]:
    """Devuelve (bloqueos, avisos). `deriva`: filas de deriva_bots (None = consultarlo)."""
    k = next((x for x in c["cuentas"] if x["id"] == cuenta_id), None)
    if k is None:
        return [f"cuenta {cuenta_id} no está en {FUENTE.name}"], []
    b, r, B, A = k.get("bot") or {}, k.get("reglas") or {}, [], []
    # 1. riesgo
    if k.get("balance") is None or r.get("piso_usd") is None:
        B.append("sin balance o sin piso declarado")
    else:
        colchon = k["balance"] - r["piso_usd"]
        if k.get("dinero_real") and not r.get("piso_verificado"):
            B.append("piso del drawdown sin verificar en el dashboard (reglas.piso_verificado)")
        sl, mx, tope = b.get("sleeves_simultaneos_max", 1), b.get("riesgo_max_por_sleeve_usd"), b.get("tope_neto_micros")
        if mx is None:
            B.append("falta bot.riesgo_max_por_sleeve_usd")
        else:
            peor = (min(sl, tope) if tope else sl) * mx
            if peor > LIM["frac_peor_caso"] * colchon:
                B.append(f"peor caso abierto ${peor:,.0f} ({sl if not tope else min(sl, tope)} x ${mx:,.0f}) > "
                         f"{LIM['frac_peor_caso']:.0%} del colchón ${colchon:,.0f}")
        dl = b.get("daily_loss_bot_usd")
        if dl is None or dl > LIM["frac_diario"] * colchon:
            B.append(f"límite diario del bot {dl} > {LIM['frac_diario']:.0%} del colchón ${colchon:,.0f}")
        dias = (hoy - date.fromisoformat(k["balance_observado"])).days if k.get("balance_observado") else None
        if dias is None or dias > c.get("umbrales", {}).get("dias_balance_vencido", 3):
            B.append(f"balance observado hace {dias} días: actualizarlo antes de decidir")
    # 2. ejecución
    inst = b.get("instrumento")
    au = [a for a in c.get("auditorias_ejecucion", []) if a.get("instrumento") == inst]
    if not inst:
        B.append("falta bot.instrumento")
    elif not au:
        B.append(f"sin auditoría de ejecución en demo para {inst} (EdgeLabExecutionProbe + tools/audit_live_execution.py)")
    else:
        a = max(au, key=lambda x: x["fecha"])
        canon = costos.friccion_rt_ticks(inst) * costos.tick_size(inst)
        if (hoy - date.fromisoformat(a["fecha"])).days > c.get("umbrales", {}).get("dias_auditoria_vencida", 14):
            B.append(f"auditoría de {inst} del {a['fecha']} vencida")
        if a.get("n", 0) < LIM["n_min_auditoria"]:
            B.append(f"auditoría de {inst} con n {a.get('n', 0)} < {LIM['n_min_auditoria']}")
        if a.get("implied_rt_pts") is None or a["implied_rt_pts"] > canon:
            B.append(f"fricción implícita {a.get('implied_rt_pts')} pts > canónica {canon:.3f} pts ({inst})")
    # 3. reglas de la firma
    hf, fl = b.get("hard_flatten_hhmm_et"), r.get("flat_hhmm_et")
    if fl is not None and (hf is None or _min(fl) - _min(hf) < LIM["minutos_antes_flat"]):
        B.append(f"cierre forzado {hf} no está {LIM['minutos_antes_flat']} min antes del flat de la firma {fl}")
    if "noticias_permitidas" not in r:
        B.append("política de noticias de la firma sin declarar (reglas.noticias_permitidas)")
    # 4. deriva repo vs instalado
    src = b.get("fuente_repo")
    if not src or not (ROOT / src).exists():
        B.append(f"fuente del bot {src} no existe en el repo")
    else:
        if deriva is None:
            import deriva_bots
            deriva = deriva_bots.revisar()
        filas = [f for f in deriva if f["repo"] == src]
        if not filas or all(f["estado"] == "NO_INSTALADO" for f in filas):
            B.append(f"{src} no está instalado en la plataforma")
        elif any(f["estado"] == "DERIVA" for f in filas):
            B.append(f"{src} instalado difiere del repo (correr tools/sync_ctrader_mt5_bots.py o revisar)")
    if not b.get("exec_audit_log", False):
        A.append("exec_audit_log apagado: no va a quedar telemetría de ejecución real")
    return B, A


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--cuenta", required=True)
    a = ap.parse_args(argv)
    B, A = evaluar(json.loads(FUENTE.read_text(encoding="utf-8")), a.cuenta, date.today())
    for x in B:
        print("BLOQUEA", x)
    for x in A:
        print("AVISO  ", x)
    print("PUERTA:", "CERRADA" if B else "ABIERTA (la activación con dinero real la decide Nico)")
    return 1 if B else 0


if __name__ == "__main__":
    sys.exit(main())
