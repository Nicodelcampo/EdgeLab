# -*- coding: utf-8 -*-
"""Inferencia de H1 sobre los outcomes ya observados. **Régimen de muerte.**

Ejecuta la parte inferencial de `docs/predictions/E-R1_v0.3.1_SELLO_2026-08-09.md`
sobre el artefacto del primer cruce legítimo (`889c048`).

> **Desde el cruce, cualquier defecto estructural acá mata H1.** Por eso este
> módulo **no implementa un solo bootstrap propio**: usa `edgelab.stats.
> cluster_estimand`, que tiene tests y es la primitiva de la enmienda
> G2-2026-08-03. Estrenar código estadístico bajo regla de muerte sería el peor
> lugar posible para hacerlo.

## Lo que el sello especifica, y que acá no se elige

```
estimando    expectativa neta por evento, friccion 2,768 ticks DENTRO
             -> trade_weighted_expectancy = sum(pnl) / sum(n_trades)
                NUNCA mean_d(u_d / v_d), que es otro estimando
inferencia   remuestreo/agrupacion por sesion; bloque minimo = dia CT
             -> studentized_stationary_interval: bootstrap-t, bloque PPW, SE HAC
sensibilidad equal-weight diaria; diferencia material SE DECLARA
multiplic.   M_eff 21,2 -> ~106, z 3,50  ->  confianza 0,999535 bilateral
decision     VIVE: IC > 0 | MUERE: IC < 0 | GRIS: contiene 0 -> MUERE
```

**`GRIS` muere por defecto.** No es un empate a resolver después: el sello lo
declara antes de ver un número, y esa es toda su fuerza.

## El calendario entra completo, con los días sin eventos

`aggregate_sessions` exige el calendario preregistrado **incluyendo días sin
trades**. No es un detalle: 201 sesiones con 424 eventos significa que muchos
días aportan `n_trades = 0`, y omitirlos inflaría el denominador por sesión y
cambiaría la dependencia que el bloque estacionario tiene que capturar.

## Qué NO se hizo antes de correr esto

**No se miró la expectativa.** El artefacto de outcomes trae el neto por evento
y nada agregado. Calcular el punto y después construir la inferencia invita a
ajustar la inferencia sabiendo el resultado; el sello las especifica a las dos,
así que no hay nada que elegir, pero el orden importa igual.

Uso:
    ./.venv/Scripts/python.exe diag/tasa_senales/inferencia_H1.py <artefacto.json>
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import platform
import sys
from pathlib import Path

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import dias_research, git_head  # noqa: E402
from edgelab.stats.cluster_estimand import (  # noqa: E402
    aggregate_sessions, percentile_interval, resample_stationary_session_clusters,
    stationary_block_length, studentized_stationary_interval,
    trade_weighted_expectancy,
)

SCHEMA_VERSION = "inferencia_H1_v1"

#: Del sello §2. `z=3,50` sale de `M_eff ~106`; la holgura por correr UNA
#: hipotesis y no tres esta declarada y **no se aprovecha**.
Z_MULTIPLICIDAD = 3.50
CONFIANZA = 0.999535          # bilateral, equivalente a z = 3,50
N_REPLICAS = 20_000
SEMILLA = 20260809            # fija y publicada: el remuestreo es reproducible


def cargar_outcomes(ruta):
    d = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not d.get("outcomes_accessed"):
        raise SystemExit("ese artefacto no observo outcomes: no hay que inferir")
    if d.get("precios_leidos", 0) <= 0:
        raise SystemExit("precios_leidos = 0: el artefacto declara sin respaldo")
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("artefacto", nargs="?", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (REPO_PATH / ".venv").resolve():
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        return 2

    ruta = a.artefacto or sorted(glob.glob(
        str(Path(__file__).resolve().parent / "runner_H1_outcomes__*.json")))[-1]
    d = cargar_outcomes(ruta)

    # CALENDARIO COMPLETO, con los dias sin eventos.
    dias, _info = dias_research()
    calendario = sorted({x["fecha"] for x in dias})

    por_sesion = {}
    n_ev = 0
    for r in d["por_contrato"].values():
        for e in (r.get("eventos") or []):
            por_sesion.setdefault(e["sesion"], []).append(float(e["neto_ticks"]))
            n_ev += 1

    fuera = sorted(set(por_sesion) - set(calendario))
    if fuera:
        raise SystemExit("eventos fuera del calendario preregistrado: %s" % fuera)

    clusters = aggregate_sessions(calendario, por_sesion)
    theta = trade_weighted_expectancy(clusters)
    b = stationary_block_length(clusters)

    print("H1  BigTrap2  T=34   INFERENCIA")
    print("  artefacto        %s" % Path(ruta).name)
    print("  sesiones         %d   con eventos %d   sin eventos %d"
          % (len(calendario), len(por_sesion), len(calendario) - len(por_sesion)))
    print("  eventos          %d" % n_ev)
    print("  bloque PPW       %d sesiones" % b)
    print("  z multiplicidad  %.2f   -> confianza %.6f bilateral"
          % (Z_MULTIPLICIDAD, CONFIANZA))
    print("  replicas         %d   semilla %d" % (N_REPLICAS, SEMILLA))

    st = studentized_stationary_interval(
        clusters, n_replicates=N_REPLICAS, seed=SEMILLA, confidence=CONFIANZA)
    lo, hi = st.lower, st.upper

    # SENSIBILIDAD declarada por el sello: equal-weight diaria contra el
    # trade-weighted. Una diferencia material SE DECLARA, no se promedia.
    dias_con = [c for c in clusters if c.n_trades > 0]
    eq = sum(c.pnl_net / c.n_trades for c in dias_con) / len(dias_con)

    print("\nESTIMANDO -- expectativa neta por evento, ticks (friccion adentro)")
    print("  trade-weighted   %+.4f" % theta)
    print("  IC %.4f%%        [%+.4f , %+.4f]" % (100 * CONFIANZA, lo, hi))
    print("  equal-weight     %+.4f   (sensibilidad, no es el estimando)" % eq)
    print("  diferencia       %+.4f" % (eq - theta))

    if lo > 0:
        veredicto, motivo = "VIVE", "la cota inferior del IC ajustado es > 0"
    elif hi < 0:
        veredicto, motivo = "MUERE", "la cota superior del IC ajustado es < 0"
    else:
        veredicto, motivo = "MUERE", ("GRIS: el IC contiene 0, y el sello declara "
                                      "que gris MUERE por defecto")

    print("\n  VEREDICTO: %s" % veredicto)
    print("  %s" % motivo)

    payload = dict(
        schema_version=SCHEMA_VERSION, hipotesis="H1",
        sello="docs/predictions/E-R1_v0.3.1_SELLO_2026-08-09.md",
        artefacto_outcomes=Path(ruta).name,
        outcomes_payload_sha256=d.get("payload_sha256"),
        sesiones=len(calendario), sesiones_con_eventos=len(por_sesion),
        eventos=n_ev,
        estimando="trade_weighted_expectancy = sum(pnl_net)/sum(n_trades)",
        theta_ticks=round(theta, 6),
        ic=dict(metodo="studentized_stationary_interval (bootstrap-t, bloque PPW, SE HAC)",
                confianza=CONFIANZA, z_multiplicidad=Z_MULTIPLICIDAD,
                bloque_ppw=b, replicas=N_REPLICAS, semilla=SEMILLA,
                lower=round(lo, 6), upper=round(hi, 6)),
        sensibilidad_equal_weight=round(eq, 6),
        diferencia_equal_weight_menos_trade_weighted=round(eq - theta, 6),
        veredicto=veredicto, motivo=motivo,
        regla="VIVE: IC>0 | MUERE: IC<0 | GRIS: contiene 0 -> MUERE",
        outcomes_accessed=True,
        code_commit=git_head(),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("inferencia_H1__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
