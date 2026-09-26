# -*- coding: utf-8 -*-
"""F0.3 — features de ESTADO sobre la serie de barras. **Primer uso en research**
de `materialize_features()` (`edgelab/bridge/features.py`, construida el
2026-07-24, trece días antes que el marco de toques que terminó usándose en
todo el corpus — ver `SESGO_DE_DISENO_2026-08-10_EL_TOQUE_COMO_UNICA_ENTRADA.md`).

## Por qué ahora, y no antes

F1.1 (nulo contra zonas aleatorias) mostró que BigTrap2 no distingue del azar
en **resistencia** (romper), pero sí, y mucho, en **atracción** (que el precio
vuelva a tocar). Eso reorienta la pregunta de "¿esta zona aguanta?" —ya cerrada,
sin señal— a "¿qué tan cerca y qué tan rodeado de zonas está el precio en cada
instante?", que es exactamente lo que estas cinco features miden, sin usar un
toque como unidad y sin leer un retorno.

## Qué mide

Sobre cada barra de las 201 sesiones, con la zona tratada como estado activo
(`created_ms <= t < ended_ms`), no como evento:

- `active_zone_count` — cuántas zonas conviven en ese instante.
- `inside_zone` — el precio está dentro de alguna.
- `distance_to_nearest_zone` — distancia en ticks al borde de la más cercana.
- `zone_age` — antigüedad de esa zona más cercana.
- `nearest_zone_side` — de qué lado (compradores/vendedores atrapados).

## Qué NO hace

No lee un retorno. No calcula P&L. `outcomes_accessed=False`, como hecho: este
módulo no tiene ninguna ruta que use un precio para juzgar un desenlace
económico — el precio sólo se usa para ubicar el estado geométrico en cada
barra, exactamente como en F1.1.

Uso:
    ./.venv/Scripts/python.exe diag/tasa_senales/F0.3_features_de_estado.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.censo_zonas_completo import resumen  # noqa: E402
from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART, bars_mod,
    corte_del_sello, dias_research, git_head, huella_del_codigo, pd, ticks_mod,
)
from edgelab.bridge.features import DEFAULT_FEATURES, materialize_features  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402

SCHEMA_VERSION = "F0.3_features_de_estado_v1"
INDICADOR = "BigTrap2"


def zonas_a_df(zones, tick_size, setf):
    """DataFrame en TICKS (no precio) con las columnas que pide
    `materialize_features`: created_ms, ended_ms, top, bottom, side."""
    filas = []
    for z in zones:
        if z.get("top") is None or z.get("created_ms") is None:
            continue
        if session_date_ct(int(z["created_ms"])) not in setf:
            continue
        filas.append(dict(
            created_ms=int(z["created_ms"]),
            ended_ms=(np.nan if z.get("ended_ms") is None else int(z["ended_ms"])),
            top=round(float(z["top"]) / tick_size),
            bottom=round(float(z["bottom"]) / tick_size),
            side=z.get("kind")))
    cols = ["created_ms", "ended_ms", "top", "bottom", "side"]
    return pd.DataFrame(filas, columns=cols) if filas else pd.DataFrame(
        {c: pd.Series(dtype="object") for c in cols})


def medir(arch, fechas):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                    + pd.Timedelta(days=1))
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())
    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / arch),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    if not bool((np.diff(np.asarray(tk.sequence)) > 0).all()):
        return dict(estado="ABSTAIN", motivo="`sequence` no es orden total")

    b = bars_mod.build_time_bars(tk, 1)
    bar_end = np.asarray(b.end_ns)
    close_t = np.asarray(b.close_t, dtype=np.float64)
    fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
    mod = REGISTRY[INDICADOR]
    r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None \
        else mod.run(tk, b, chart_tz=TZ_CHART)

    setf = set(fechas)
    bar_ms = (bar_end // 1_000_000).astype(np.int64)

    # Recortar a barras de las sesiones pedidas -- excluye el lead-in de warmup,
    # igual que todo el resto del programa.
    ses_de_barra = np.array([session_date_ct(int(t)) for t in bar_ms], dtype=object)
    en_calendario = np.isin(ses_de_barra, list(setf))
    if not en_calendario.any():
        return dict(estado="ABSTAIN", motivo="sin barras en calendario")

    zdf = zonas_a_df(r.get("zones") or [], tk.tick_size, setf)
    feats = materialize_features(zdf, bar_ms[en_calendario], price=close_t[en_calendario],
                                 features=DEFAULT_FEATURES, tick_size=tk.tick_size)

    hora_ct = (pd.to_datetime(bar_ms[en_calendario], unit="ms", utc=True)
              .tz_convert("America/Chicago").hour)
    por_hora = Counter()
    for h, azc, ins in zip(hora_ct, feats["active_zone_count"].to_numpy(),
                           feats["inside_zone"].to_numpy()):
        c = por_hora.setdefault(int(h), Counter())
        c["n"] += 1
        c["azc_sum"] += int(azc)
        c["inside_n"] += int(ins)

    lado = Counter(x for x in feats["nearest_zone_side"].dropna().tolist())

    return dict(
        estado="OK", sesiones=len(fechas), n_barras=int(en_calendario.sum()),
        active_zone_count=resumen(feats["active_zone_count"].tolist()),
        inside_zone_frac=float(feats["inside_zone"].mean()),
        distance_to_nearest_zone=resumen(
            feats["distance_to_nearest_zone"].dropna().tolist()),
        zone_age_barras=resumen(
            (feats["zone_age"].dropna() / (60_000)).tolist()),   # ms -> minutos = barras (time:1)
        nearest_zone_side=dict(lado),
        por_hora_ct={str(k): dict(v) for k, v in por_hora.items()},
        cobertura_con_zona_activa=float((feats["active_zone_count"] > 0).mean()))


def combinar_resumenes(lista_resumenes):
    """Reconstituye un resumen agregado desde resumenes por-contrato con pesos
    por n. Aproximado para percentiles (promedio ponderado, no exacto), exacto
    para media/min/max -- se declara la limitacion en el payload."""
    total_n = sum(r["n"] for r in lista_resumenes)
    if not total_n:
        return None
    media = sum(r["media"] * r["n"] for r in lista_resumenes) / total_n
    out = dict(n=total_n, media=round(media, 4),
              min=min(r["min"] for r in lista_resumenes),
              max=max(r["max"] for r in lista_resumenes))
    for q in (10, 25, 50, 75, 90):
        k = "p%d" % q
        out[k] = round(sum(r[k] * r["n"] for r in lista_resumenes) / total_n, 4)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (REPO_PATH / ".venv").resolve():
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        return 2

    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(x, sorted(f)) for x, f in sorted(por_arch.items())]
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _x, fs in plan)

    print("F0.3  FEATURES DE ESTADO -- materialize_features(), primer uso en research")
    print("  universo %d sesiones" % ns)

    crudo = {}
    azc_list, dist_list, age_list = [], [], []
    lado_tot, hora_tot = Counter(), {}
    inside_w, cov_w = [], []
    n_barras_tot = 0
    for arch, fechas in plan:
        print("\n== %s : %d sesiones" % (arch, len(fechas)), flush=True)
        res = medir(arch, fechas)
        crudo[arch] = res
        if res.get("estado") != "OK":
            print("   %s: %s" % (res["estado"], res.get("motivo")))
            continue
        n_barras_tot += res["n_barras"]
        azc_list.append(res["active_zone_count"])
        dist_list.append(res["distance_to_nearest_zone"])
        age_list.append(res["zone_age_barras"])
        lado_tot.update(res["nearest_zone_side"])
        inside_w.append((res["inside_zone_frac"], res["n_barras"]))
        cov_w.append((res["cobertura_con_zona_activa"], res["n_barras"]))
        for h, c in res["por_hora_ct"].items():
            ht = hora_tot.setdefault(h, Counter())
            ht.update(c)
        print("   barras=%d   active_zone_count med=%.1f   cobertura=%.1f%%   inside=%.2f%%"
              % (res["n_barras"], res["active_zone_count"]["p50"],
                 100 * res["cobertura_con_zona_activa"], 100 * res["inside_zone_frac"]))

    azc = combinar_resumenes(azc_list)
    dist = combinar_resumenes(dist_list)
    age = combinar_resumenes(age_list)
    inside_frac = sum(v * n for v, n in inside_w) / sum(n for _v, n in inside_w)
    cobertura = sum(v * n for v, n in cov_w) / sum(n for _v, n in cov_w)

    print("\n" + "=" * 70)
    print("AGREGADO  (%d barras, %d sesiones)" % (n_barras_tot, ns))
    print("  active_zone_count   mediana %.1f  media %.2f  p90 %.1f  max %.0f"
          % (azc["p50"], azc["media"], azc["p90"], azc["max"]))
    print("  cobertura (>=1 zona activa)   %.2f%%" % (100 * cobertura))
    print("  inside_zone (precio DENTRO de alguna)   %.2f%%" % (100 * inside_frac))
    print("  distance_to_nearest_zone (ticks)   mediana %.2f  p90 %.2f"
          % (dist["p50"], dist["p90"]))
    print("  zone_age de la mas cercana (barras)   mediana %.1f  p90 %.1f"
          % (age["p50"], age["p90"]))
    print("  lado de la mas cercana   %s" % dict(lado_tot))

    print("\n  estacionalidad intradia (hora CT) -- active_zone_count medio, cobertura")
    for h in sorted(hora_tot, key=int):
        c = hora_tot[h]
        print("    %2sh  n=%6d  azc_med=%.2f  inside=%.2f%%"
              % (h, c["n"], c["azc_sum"] / c["n"], 100 * c["inside_n"] / c["n"]))

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F0.3",
        que_es="features de ESTADO (materialize_features) sobre la serie de "
               "barras -- primer uso en research. Sin retornos.",
        plan="docs/PLAN_ANALISIS_v2_2026-08-10.md",
        motivo="F1.1 mostro que BigTrap2 distingue del azar en ATRACCION "
               "(tocar) no en RESISTENCIA (romper); estas features miden "
               "confluencia/cercania, el eje que importa segun ese resultado.",
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        universe_filter_report=info, outcomes_accessed=False,
        n_barras=n_barras_tot,
        active_zone_count=azc, cobertura_con_zona_activa=round(cobertura, 6),
        inside_zone_frac=round(inside_frac, 6),
        distance_to_nearest_zone_ticks=dist, zone_age_barras=age,
        nearest_zone_side=dict(lado_tot),
        estacionalidad_por_hora_ct={h: dict(c) for h, c in hora_tot.items()},
        limitacion_percentiles_agregados="percentiles del agregado son promedio "
            "ponderado por contrato, no recalculo exacto sobre el pool completo",
        por_contrato=crudo,
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F0.3_features_estado__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
