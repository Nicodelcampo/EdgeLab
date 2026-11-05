#!/usr/bin/env python3
"""Mirada EXPLORATORIA al holdout de una campaña del embudo (decisión de Nico, 2026-10-26: «mirar igual, sabiendo el costo»).

  python tools/holdout_exploratorio.py <raiz_embudo> <CID> --hasta YYYYMMDD --sellado '{"DK:USA500IDXUSD": "...", "NQ": "..."}'

Orden (todo queda escrito ANTES de ver un número):
  1. anula la apertura confirmatoria vigente de la familia (todavía sin mirar: `holdout_ventanas.anular_apertura`);
  2. escribe `ACTA_HOLDOUT_EXPLORATORIO.json` (regla congelada, ventana, motivo) y registra la ventana como `consumida`;
  3. corre la regla congelada (celda + cortes + tope de la campaña) sobre los datos sellados con el motor de la grilla
     (el mismo que la eligió: entradas límite y tope tick a tick) y escribe `RESULTADO_HOLDOUT_EXPLORATORIO.json`;
  4. mueve `holdout.desde` de la campaña al día siguiente de lo mirado y la devuelve a ACTA: la confirmación, si se hace, usa
     sesiones NUEVAS y vuelve a pasar la compuerta de potencia.
El resultado NO confirma ni refuta (exploratorio, sin paso de LORD++); sólo informa. Datos: sólo en la máquina con la carpeta sellada.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT  # noqa: E402

DECISION = "Decisión de Nico 2026-10-26: mirada exploratoria al holdout sabiendo que consume esas sesiones para la familia."


def preparar(raiz: Path, cid: str, hasta: int, ventanas=None, ahora=time.time) -> dict:
    """Pasos 1–2 (sin datos). Devuelve el acta."""
    from edgelab.research import holdout_ventanas as HV
    libro = Path(ventanas) if ventanas else HV.LIBRO
    d = raiz / cid; st = json.loads((d / "estado.json").read_text(encoding="utf-8")); spec = st["spec"]; fam = spec["familia"]
    if st.get("n_holdout") or st.get("ultimo_conteo"): raise SystemExit(f"{cid}: el holdout ya se contó; no se re-mira")
    if (d / "ACTA_HOLDOUT_EXPLORATORIO.json").exists(): raise SystemExit(f"{cid}: ya tiene mirada exploratoria")
    if not st.get("regla"): raise SystemExit(f"{cid}: sin regla congelada (no pasó TOPES)")
    desde = int(((st.get("reglas") or {}).get("holdout") or {}).get("desde") or HOLDOUT_PRIMERA_SESION_INT)
    if int(hasta) < desde: raise SystemExit(f"hasta {hasta} < desde {desde}")
    if any(r["cid"] == cid for r in HV.aperturas_vigentes(fam, libro)):
        HV.anular_apertura(fam, cid, f"antes de la mirada exploratoria ({DECISION})", 0, libro)
    acta = dict(cid=cid, familia=fam, regla=st["regla"], cortes=st["cortes"], experimento=spec["experimento"], sensor=spec["sensor"],
                ejecucion=spec.get("ejecucion"), desde=desde, hasta=int(hasta), tipo="exploratoria", decision=DECISION, registrada=ahora(),
                efecto="no confirma ni refuta; consume las sesiones para la familia; la confirmación usa sesiones posteriores")
    (d / "ACTA_HOLDOUT_EXPLORATORIO.json").write_text(json.dumps(acta, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    row = dict(tipo="consumida", familia=fam, desde=desde, hasta=int(hasta), relacionadas=[], motivo=f"mirada exploratoria {cid}: {DECISION}",
               ts=ahora())
    with libro.open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return acta


def correr(raiz: Path, cid: str, sellado: dict, runner=None) -> dict:
    """Paso 3: la regla congelada sobre los datos sellados (LocalRunner, etapa REP con el tope de la regla)."""
    from edgelab.funnel.escalera import resumen_sesiones
    from edgelab.research import embudo_runners as ER
    d = raiz / cid; acta = json.loads((d / "ACTA_HOLDOUT_EXPLORATORIO.json").read_text(encoding="utf-8"))
    spec = json.loads((d / "estado.json").read_text(encoding="utf-8"))["spec"]
    if runner is None:
        lec, tk = ER.lectores_sellados(sellado, raiz); runner = ER.LocalRunner(lec, tk, carpeta=raiz / "_local", acta_requerida=False)
    h = runner.lanzar(spec, "REP", dict(cortes=acta["cortes"], celdas=[acta["regla"]["celda"]], tope=acta["regla"].get("tope")),
                      [acta["desde"], acta["hasta"]])
    res = runner.traer(h); ops = res.get("operaciones") or {}
    import numpy as np
    x = np.asarray(ops.get("neto", []), float); ses = np.asarray(ops.get("ses", []))
    out = dict(cid=cid, ventana=[acta["desde"], acta["hasta"]], n=int(len(x)), sesiones=int(len(set(ses.tolist()))),
               media=float(x.mean()) if len(x) else None, total=float(x.sum()) if len(x) else 0.0,
               ganadoras=int((x > 0).sum()), operaciones=[float(v) for v in x], tipo="exploratorio: no confirma ni refuta")
    if len(x) >= 5:
        rs = resumen_sesiones(x, ses, n_boot=5000); out.update(ic90=rs["ic"], p=rs["p_unilateral"])
    (d / "RESULTADO_HOLDOUT_EXPLORATORIO.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    return out


def cerrar(raiz: Path, cid: str, campanas: Path = ROOT / "config/autopilot/grillas/campanas") -> int:
    """Paso 4: la confirmación pasa a sesiones posteriores a lo mirado; la campaña vuelve a ACTA (compuerta de potencia)."""
    import datetime as dt
    d = raiz / cid; acta = json.loads((d / "ACTA_HOLDOUT_EXPLORATORIO.json").read_text(encoding="utf-8"))
    nuevo = int((dt.date(acta["hasta"] // 10000, acta["hasta"] // 100 % 100, acta["hasta"] % 100) + dt.timedelta(days=1)).strftime("%Y%m%d"))
    st = json.loads((d / "estado.json").read_text(encoding="utf-8"))
    if st.get("acta"):
        (d / "ACTA_HOLDOUT.json").exists() and (d / "ACTA_HOLDOUT.json").rename(d / "ACTA_HOLDOUT_ANULADA_EXPLORATORIO.json")
        st.setdefault("actas_anuladas", []).append(st.pop("acta"))
    st["spec"]["holdout"]["desde"] = nuevo; st["reglas"]["holdout"]["desde"] = nuevo
    st["historial"].append(dict(ts=time.time(), decision_humana=DECISION, campo="holdout.desde", a=nuevo))
    st.update(etapa="ACTA", fase="PENDIENTE", handle=None, fallas=0)
    (d / "estado.json").write_text(json.dumps(st, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    fj = Path(campanas) / f"{cid}.json"
    if fj.exists():
        camp = json.loads(fj.read_text(encoding="utf-8")); camp["holdout"]["desde"] = nuevo
        camp.setdefault("decisiones", []).append(f"{DECISION} Confirmación desde {nuevo}.")
        fj.write_text(json.dumps(camp, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    with (d / "MEDIDO.md").open("a", encoding="utf-8") as f:
        f.write(f"- HOLDOUT EXPLORATORIO {acta['desde']}–{acta['hasta']} (no confirma ni refuta; {DECISION}): ver RESULTADO_HOLDOUT_EXPLORATORIO.json; "
                f"la confirmación pasa a sesiones desde {nuevo}\n")
    return nuevo


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("raiz"); ap.add_argument("cid"); ap.add_argument("--hasta", type=int, required=True)
    ap.add_argument("--sellado", required=True); a = ap.parse_args(); raiz = Path(a.raiz)
    preparar(raiz, a.cid, a.hasta)
    out = correr(raiz, a.cid, json.loads(a.sellado))
    nuevo = cerrar(raiz, a.cid)
    print(json.dumps({k: v for k, v in out.items() if k != "operaciones"}, indent=1, ensure_ascii=False, default=float))
    print(f"confirmación desde {nuevo}; commitear los archivos de {raiz / a.cid}, config/autopilot/grillas/campanas y HOLDOUT_VENTANAS")


if __name__ == "__main__":
    main()
