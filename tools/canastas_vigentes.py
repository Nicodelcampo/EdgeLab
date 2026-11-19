#!/usr/bin/env python3
"""Documento único y auditable de las canastas vigentes (pedido de Nico, 2026-11-17: «subí las canastas a donde se lean y puedan auditar»).
Se GENERA de los archivos que la operación usa (no se edita a mano): CARTERA_V2/V3_OPERATIVA.json y BATERIA.json (cartera_20261116),
CARTERA_B_OPERATIVA.json y las operaciones de FundedSync (fundedsyncstack_20261115), y la simulación de Lucid (CANASTAS_LUCID.json).
  python tools/canastas_vigentes.py --write     # -> docs/cartera/CANASTAS_VIGENTES.md (tests/research/test_canastas_vigentes.py lo exige al día)
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; SALIDA = ROOT / "docs/cartera/CANASTAS_VIGENTES.md"
C = ROOT / "docs/research/cartera_20261116"; F = ROOT / "docs/research/fundedsyncstack_20261115"; L = ROOT / "docs/research/propfirm_lucidflex_20261117"


def _j(p): return json.loads(Path(p).read_text(encoding="utf-8"))


def _f(x, d=2): return "—" if x is None else (f"{x:+.{d}f}" if isinstance(x, float) else str(x))


def _n(x, d=1, pct=False): return "—" if x is None else (f"{x:.0%}" if pct else f"{x:.{d}f}")


def _tabla_v(op):
    sys.path.insert(0, str(ROOT / "tools")); from cartera_nov import OPS, DEV_PREVIO
    B = {b["cid"]: b for b in _j(C / "BATERIA.json")["reglas"]}
    out = ["| Regla | Señal → ejecuta | Micros | Riesgo mediano | No operar si stop < | R/op DESC (t) | R/op REP (t) | R/op oct | Fricción R | Meses + | Ops/mes | Operaciones (auditar) |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in op["reglas"]:
        b = B.get(r["regla"], {}); de, rp, oc = b.get("desc", {}), b.get("rep", {}), b.get("oct", {})
        ops = ", ".join(f"`{p.relative_to(ROOT)}`" for p in sorted({*Path(DEV_PREVIO).glob(f"{r['regla']}__*.json"), *Path(OPS).glob(f"{r['regla']}__*.json")}))
        out.append(f"| {r['regla']} | {r['senal']} → {r['ejecuta']} | {r['micros']}{' ×' + str(r['peso']) if r.get('peso', 1) != 1 else ''} | "
                   f"{r['usd_riesgo_mediano']} USD | {r['no_operar_si_stop_menor_a_pts']} pts | {_f(de.get('R_op'))} ({_f(de.get('t_ses'), 1)}) | "
                   f"{_f(rp.get('R_op'))} ({_f(rp.get('t_ses'), 1)}) | {_f(oc.get('R_op'))} | {_f(b.get('friccion_R'), 3)} | "
                   f"{_n(b.get('meses_pos'), pct=True)} | {_n(b.get('ops_mes'))} | {ops or '—'} |")
    return out


def _tabla_b():
    import numpy as np, pandas as pd
    o = pd.read_csv(F / "cadena/FUNDEDSYNC_OPS.csv.gz", usecols=["dia", "neto", "modulo"]); o = o[o.modulo.isin(["T", "Z", "R"]) & (o.dia >= "2020-01-01")]
    out = ["| Regla | Módulo | Micros MNQ | Stop | Pts/op 2020–23 (t) | Pts/op 2024–26 (t) | Ops/mes |", "|---|---|---|---|---|---|---|"]
    op = _j(F / "CARTERA_B_OPERATIVA.json")
    for r in op["reglas"]:
        g = o[o.modulo == r["regla"]]; a, b = g[g.dia < "2024-01-01"].neto, g[g.dia >= "2024-01-01"].neto
        t = lambda x: x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 else float("nan")
        meses = max(1, (pd.Timestamp(g.dia.max()) - pd.Timestamp(g.dia.min())).days / 30.44)
        out.append(f"| {r['regla']} | {r['modulo']} | {r['micros']} | {r['stop']} | {a.mean():+.1f} ({t(a):.1f}) | {b.mean():+.1f} ({t(b):.1f}) | {len(g) / meses:.1f} |")
    return out


def _lucid():
    p = L / "CANASTAS_LUCID.json"
    if not p.exists(): return ["(sin simulación de Lucid todavía: `python tools/lucid_canastas.py`)"]
    d = _j(p)["canastas"]
    out = ["Valor esperado por cuenta comprada (USD), LucidFlex 25K con **DLL $600 + 50 % ($55,30)**, retirando $1.000; media de desarrollo / "
           "**contraída** (James-Stein ≈ mitad; el paso 2 de `urgencia_vs_evidencia_20261117` mostró que es OPTIMISTA: lo elegido no conservó nada en réplica, así que la expectativa honesta hoy está entre «cero» y «contraída» hasta que decida el forward) / cero (sin edge). Detalle de las 4 configuraciones y las dos políticas en "
           "`docs/research/propfirm_lucidflex_20261117/CANASTAS_LUCID.json`.", "",
           "| Canasta | USD/sesión (t) | Pasa (contraída) | Cobra (contraída) | EV dev | **EV contraída** | EV cero | Días por cuenta | EV contraída por mes y cuenta |",
           "|---|---|---|---|---|---|---|---|---|"]
    for k, r in d.items():
        v = r["variantes"]; a, c, z = v["DLL600|50%|dev|max"], v["DLL600|50%|contraida|max"], v["DLL600|50%|cero|max"]
        out.append(f"| {k} | {r['usd_sesion_media']:+.0f} ({r['t']:.1f}) | {c['pasa']:.0%} | {c['cobra']:.0%} | {a['ev']:+.0f} | **{c['ev']:+.0f}** | "
                   f"{z['ev']:+.0f} | {c['dias_total']:.0f} | {c['ev_por_mes']:+.0f} |")
    return out


def render() -> str:
    v2, v3 = _j(C / "CARTERA_V2_OPERATIVA.json"), _j(C / "CARTERA_V3_OPERATIVA.json"); b = _j(F / "CARTERA_B_OPERATIVA.json")
    md = ["# Canastas vigentes — qué se opera, con qué evidencia y cómo auditarlo", "",
          "Estado: VIGENTE (GENERADO por `python tools/canastas_vigentes.py --write` de los archivos que usa la operación; no editar a mano). "
          "0 edges promovidos: todas en papel/forward; operar con dinero real lo decide Nico. North Star sha256 "
          "`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.", "",
          "## Cómo auditar", "",
          "- Cada número sale de un archivo committeado (columna «Operaciones»); el historial de git dice quién y cuándo lo cambió.",
          "- Pre-registros (escritos antes de mirar): `docs/research/cartera_20261116/PREREGISTRO.md`, `PREREGISTRO_TANDA4.md`, `PREREGISTRO_FORWARD_V2.md`, "
          "`docs/research/fundedsyncstack_20261115/PREREGISTRO_CARTERA_B.md`; aperturas del holdout en `docs/research/HOLDOUT_VENTANAS.jsonl`; pruebas "
          "contadas en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl`.",
          "- Recalcular: `python tools/cartera_nov_analisis.py seleccion|noviembre|prop`, `python tools/fundedsync_cadena.py cartera_b <AAAAMMDD>`, "
          "`python tools/lucid_canastas.py`, `python tools/seguimiento_forward.py <AAAAMMDD>` (forward bajo demanda).",
          "- Costos: sólo `config/costos/costos_canonicos.json` (`edgelab/costos.py`).", "",
          f"## Cartera v2 ({v2['fecha']}) — {len(v2['reglas'])} reglas, base de `{v2['base']}`", "",
          "Mejoras aplicadas: " + "; ".join(v2["mejoras"]) + ".", ""] + _tabla_v(v2) + [
          "", "Fricción R = fricción mediana antes del filtro M1 (con M1 no se opera cuando supera 0,08 R).", "",
          f"## Cartera v3 ({v3['fecha']}) — {len(v3['reglas'])} reglas (forward en paralelo con la v2), base de `{v3['base']}`", ""] + _tabla_v(v3) + [
          "", f"## Cartera B ({b['fecha']}) — T + Z + R de FundedSync en {b['instrumento']} (canasta aparte, otra lógica de riesgo)", "",
          f"Pre-registro: `{b['preregistro']}`. Variante paralela: {b['variante_paralela']}. Cuenta de referencia: {b['cuenta_referencia']}. "
          "Puntos netos de fricción canónica por operación (desarrollo sin el stop de catástrofe de Z y R).", ""] + _tabla_b() + [
          "", "## En una cuenta LucidFlex 25K (simulación, descriptiva)", ""] + _lucid() + [
          "", "## Lo que NO está demostrado (leer antes de operar)", "",
          "- Ninguna canasta tiene confirmación fuera de muestra con potencia: el holdout de oct–nov es corto y a favor; decide el forward.",
          "- La media de desarrollo viene de reglas elegidas entre muchas: usar la columna **contraída**, no la de desarrollo.",
          "- La vida de una ventaja en este dominio (NQ/ES intradía) todavía no está medida (paso 1b de "
          "`docs/research/urgencia_vs_evidencia_20261117/PROPUESTA.md`).", ""]
    return "\n".join(md)


if __name__ == "__main__":
    t = render()
    if "--write" in sys.argv: SALIDA.parent.mkdir(parents=True, exist_ok=True); SALIDA.write_text(t, encoding="utf-8"); print("escrito", SALIDA.relative_to(ROOT))
    else: print(t)
