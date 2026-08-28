# -*- coding: utf-8 -*-
"""PreRange double-sweep — formal, symmetric-by-construction reversion race.

El problema del analisis original: "tasa de doble barrido = 72%" es una
TAUTOLOGIA GEOMETRICA. Una difusion cruza los bordes de un rango angosto con
alta frecuencia; el nulo browniano ya daba 68% y el exceso era p=0.103. Peor:
condicionar por "rango comprimido" sube la tasa porque las fronteras estan mas
cerca, no porque haya liquidez.

El fix (misma disciplina que F2.7): NO medir la frecuencia del barrido. Medir,
DESPUES del segundo barrido, una carrera de primer pasaje SIMETRICA POR
CONSTRUCCION alrededor del close de esa barra:

    anchor = close(barra del segundo barrido)   [enteros de tick]
    revert = anchor - d   (hacia adentro del rango)   si el 2do barrido fue arriba
    cont   = anchor + d   (hacia afuera)
    (espejado si el 2do barrido fue abajo)

Bajo difusion sin drift, P(revert primero) = P(cont primero) exactamente.
El nulo es 0 por geometria: no hay que simular brownianos ni estimar vol.
Cualquier asimetria es el efecto. La compresion deja de estar en el numerador
porque d escala con el rango.

El segundo problema: la ventana 08:12-09:12 fue elegida a ojo. Un p-value sobre
una ventana elegida mirando datos no es interpretable. Fix: familia de PLACEBO
WINDOWS (mismo estimando, otros horarios de arranque). La ventana primaria debe
GANARLE a la distribucion de placebos; el rank del primario entre K+1 candidatos
es un p-value de permutacion que absorbe la seleccion.

agregacion: media por sesion (ceros adentro), HAC Bartlett, IC95.
outcomes_accessed=False, pnl_accessed=False (esto NO mide P&L).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = "prerange_sweep_formal_v0_1"

# ---- parametros preregistrados (NO se barren) ----
PRIMARY_START_MIN = 8 * 60 + 12      # 08:12 en el reloj declarado
WINDOW_DUR_MIN = 60                  # 60 min -> 09:12
# Familia de placebos: grilla de 30m, excluyendo los que se solapan con la
# ventana primaria (|off| < duracion). 25 placebos -> piso de p_perm = 1/26 =
# 0.038 < 0.05. Con 8 placebos el piso habria sido 1/9 = 0.111 y ningun
# resultado, ni perfecto, podria haber sido significativo.
PLACEBO_OFFSETS = [o for o in range(-480, 331, 30) if abs(o) >= WINDOW_DUR_MIN]
SESSION_END_MIN = 16 * 60            # 16:00: fin del horizonte de carrera
D_FRAC = 0.5                         # d = 0.5 * rango de la ventana
MIN_WINDOW_BARS = 45                 # cobertura minima de la ventana de 60m
MIN_POST_BARS = 60
MIN_SESSIONS = 30
RESOLUTION_MIN = 0.30
TIE_FRAC_MAX = 0.10
COVERAGE_MIN = 0.40                  # sesiones con doble barrido / sesiones validas
# Sin suficientes placebos utilizables el p-value de permutacion tiene un piso
# demasiado alto y PRERANGE_EDGE seria inalcanzable o, peor, se emitiria con un
# p_perm que nunca pudo bajar de 0.05. 19 placebos -> piso 1/20 = 0.05.
MIN_USABLE_PLACEBOS = 19

# ---- procedencia de la ventana: determina el TECHO de la etiqueta ----
#   a_priori_external  : publicada / vista antes de tocar estos datos. La
#                        seleccion la hizo un tercero sobre datos desconocidos,
#                        asi que el rank contra placebos SI es interpretable
#                        sobre estos datos (pero ver T5: publication bias).
#   a_priori_mechanism : derivada de un mecanismo declarado antes de mirar datos.
#   chosen_from_this_data : elegida mirando estos mismos datos. El rank ya esta
#                        comprometido -> techo PRERANGE_WINDOW_UNSPECIFIC.
#   unknown            : se asume lo peor.
PROVENANCE_ALLOWING_EDGE = ("a_priori_external", "a_priori_mechanism")

# ---- estratos estructurales de la familia, declarados ANTES de correr ----
# LEMA DE IDENTIFICACION (geometrico, no empirico): una ventana de 60m que
# contenga las 08:30 debe arrancar entre 07:31 y 08:30, o sea a MENOS de 60m de
# la primaria (08:12), o sea que se solapa y por lo tanto esta excluida de la
# familia de placebos. Conclusion: NINGUN placebo puede contener la publicacion
# de 08:30. La familia de placebos NO puede separar "absorcion de liquidez" de
# "reaccion al dato macro". Eso se identifica con el split por dia con/sin
# evento programado (--macro-dates), nunca con los placebos.
MACRO_RELEASE_MIN = 8 * 60 + 30      # 08:30
CASH_OPEN_MIN = 9 * 60 + 30          # 09:30 apertura del cash
RTH_START_MIN = 7 * 60               # antes de esto: liquidez overnight


def price_to_tick(price, tick):
    """Half-tick-safe. Nunca round() de Python sobre price/tick (banker's)."""
    return int(math.floor(float(price) / tick + 0.5))


# ---------------------------------------------------------------- parsing

_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y%m%d %H%M%S", "%Y%m%d %H%M",
)


def parse_time(text):
    t = (text or "").strip()
    if "T" in t:
        t = t[:19]
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    raise ValueError("unparseable time: %r" % text)


def _sniff(line):
    return ";" if line.count(";") > line.count(",") else ","


def load_m1(path, tick):
    """CSV con header (Time,Open,High,Low,Close[,Volume]) o export NT8 headerless."""
    lines = [l for l in Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    if not lines:
        raise RuntimeError("empty file %s" % path)
    bars = []
    if any(c.isalpha() for c in lines[0]):
        for row in csv.DictReader(lines, delimiter=_sniff(lines[0])):
            t = row.get("Time") or row.get("time") or row.get("Date")
            h, l, c = row.get("High"), row.get("Low"), row.get("Close")
            if not (t and h and l and c):
                continue
            bars.append((parse_time(t), float(h), float(l), float(c)))
    else:
        d = _sniff(lines[0])
        for ln in lines:
            p = ln.split(d)
            if len(p) < 5:
                continue
            bars.append((parse_time(p[0].strip()), float(p[2]), float(p[3]), float(p[4])))
    if not bars:
        raise RuntimeError("no bars parsed from %s" % path)
    bars.sort(key=lambda b: b[0])
    out = []
    seen = set()
    for t, h, l, c in bars:
        if t in seen:
            continue
        seen.add(t)
        out.append(dict(
            time=t,
            hi=price_to_tick(h, tick), lo=price_to_tick(l, tick), cl=price_to_tick(c, tick),
            mod=t.hour * 60 + t.minute, date=t.date(),
        ))
    return out


def group_sessions(bars):
    ses = {}
    for b in bars:
        ses.setdefault(b["date"], []).append(b)
    return [(d, ses[d]) for d in sorted(ses)]


def load_macro_dates(path):
    """CSV/txt con una fecha YYYY-MM-DD por linea (o en la primera columna)."""
    out = set()
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        tok = ln.split(",")[0].strip()
        if not tok or any(c.isalpha() for c in tok):
            continue
        try:
            out.add(datetime.strptime(tok, "%Y-%m-%d").date())
        except ValueError:
            continue
    return out


def classify_window(start_min, dur_min=WINDOW_DUR_MIN):
    """Estrato estructural de una ventana. Declarado a priori, no elegido
    mirando resultados. Ver LEMA DE IDENTIFICACION arriba."""
    end = start_min + dur_min
    if start_min <= MACRO_RELEASE_MIN < end:
        return "contains_0830_macro"
    if start_min <= CASH_OPEN_MIN < end:
        return "contains_0930_cash_open"
    if start_min < RTH_START_MIN:
        return "overnight"
    return "rth_quiet"


# ---------------------------------------------------------------- estimand

def detect_double_sweep(day_bars, start_min, dur_min):
    """Devuelve el evento de doble barrido de la sesion, o un motivo de descarte.

    non_repainting: todo se decide con barras ya cerradas; el evento existe
    recien en la barra del segundo barrido (available_at = su close).
    """
    end_min = start_min + dur_min
    win = [b for b in day_bars if start_min <= b["mod"] < end_min]
    if len(win) < MIN_WINDOW_BARS:
        return None, "window_coverage"
    w_hi = max(b["hi"] for b in win)
    w_lo = min(b["lo"] for b in win)
    rng = w_hi - w_lo
    if rng <= 0:
        return None, "degenerate_range"

    post = [b for b in day_bars if end_min <= b["mod"] <= SESSION_END_MIN]
    if len(post) < MIN_POST_BARS:
        return None, "post_coverage"

    first_side = None
    for i, b in enumerate(post):
        up = b["hi"] >= w_hi
        dn = b["lo"] <= w_lo
        if first_side is None:
            if up and dn:
                return None, "first_bar_both_sides"   # no resoluble en M1
            if up:
                first_side = "upper"
            elif dn:
                first_side = "lower"
            continue
        # ya hubo primer barrido: buscamos el opuesto
        if (first_side == "upper" and dn) or (first_side == "lower" and up):
            second_side = "lower" if first_side == "upper" else "upper"
            return dict(
                idx=i, post=post, w_hi=w_hi, w_lo=w_lo, rng=rng,
                first_side=first_side, second_side=second_side,
                anchor=b["cl"], time=b["time"],
            ), None
    return None, "no_double_sweep" if first_side else "no_sweep"


def reversion_race(ev, d_frac=D_FRAC):
    """Carrera simetrica desde el close del segundo barrido.

    Bajo difusion sin drift el resultado esperado es exactamente 0.
    r=+1 revierte primero (hacia adentro), -1 continua, 0 empate/sin resolver.
    """
    d = int(round(ev["rng"] * d_frac))
    if d < 1:
        return None, "d_too_small"
    a = ev["anchor"]
    if ev["second_side"] == "upper":
        # el segundo barrido rompio ARRIBA -> revertir es bajar
        revert, cont = a - d, a + d
    else:
        revert, cont = a + d, a - d

    hit_r = hit_c = None
    for j in range(ev["idx"] + 1, len(ev["post"])):
        b = ev["post"][j]
        if hit_r is None and b["lo"] <= revert <= b["hi"]:
            hit_r = j
        if hit_c is None and b["lo"] <= cont <= b["hi"]:
            hit_c = j
        if hit_r is not None or hit_c is not None:
            break
    if hit_r is None and hit_c is None:
        return 0.0, "double_censor"
    if hit_r is not None and hit_c is not None:
        return 0.0, "tie_same_bar"
    if hit_r is not None:
        return 1.0, "revert_first"
    return -1.0, "cont_first"


# ---------------------------------------------------------------- inference

def hac_bartlett_ci(values):
    n = len(values)
    if n < MIN_SESSIONS:
        return dict(mean=None, se_hac=None, ci95_lower=None, ci95_upper=None,
                    lag=None, n_sessions=n, abstain_inferencia=True)
    mean = sum(values) / n
    L = max(1, math.ceil(math.sqrt(n)))
    dv = [v - mean for v in values]
    var = sum(t * t for t in dv) / n
    for k in range(1, L + 1):
        g = sum(dv[t] * dv[t - k] for t in range(k, n)) / n
        var += 2.0 * (1.0 - k / (L + 1)) * g
    se = math.sqrt(max(var / n, 0.0))
    return dict(mean=mean, se_hac=se, ci95_lower=mean - 1.96 * se,
                ci95_upper=mean + 1.96 * se, lag=L, n_sessions=n,
                abstain_inferencia=False)


def run_window(sessions, start_min, dur_min=WINDOW_DUR_MIN, d_frac=D_FRAC):
    rows, cats, skips = [], {}, {}
    n_valid = 0
    for date, day in sessions:
        ev, why = detect_double_sweep(day, start_min, dur_min)
        if ev is None:
            skips[why] = skips.get(why, 0) + 1
            if why in ("no_double_sweep", "no_sweep", "first_bar_both_sides"):
                n_valid += 1
            continue
        n_valid += 1
        r, cat = reversion_race(ev, d_frac)
        if r is None:
            skips[cat] = skips.get(cat, 0) + 1
            continue
        cats[cat] = cats.get(cat, 0) + 1
        rows.append(dict(date=date, r=r, cat=cat, rng=ev["rng"],
                         weekday=date.weekday(), second_side=ev["second_side"]))

    ses_means = [r["r"] for r in rows]  # una observacion por sesion
    ic = hac_bartlett_ci(ses_means)
    n = len(rows)
    decided = cats.get("revert_first", 0) + cats.get("cont_first", 0)
    return dict(
        start_min=start_min,
        start_hhmm="%02d:%02d" % (start_min // 60, start_min % 60),
        n_events=n, n_valid_sessions=n_valid,
        coverage=n / n_valid if n_valid else 0.0,
        ic=ic, cats=cats, skips=skips,
        n_decided=decided,
        frac_resolved=decided / n if n else 0.0,
        frac_tie=cats.get("tie_same_bar", 0) / n if n else 0.0,
        p_revert_over_decided=(cats.get("revert_first", 0) / decided) if decided else None,
        rows=rows,
    )


def stratify(rows, key, buckets=None):
    """Descriptivo: medias por estrato. NO adjudica (multiplicidad no corregida)."""
    out = {}
    if key == "range_median":
        if not rows:
            return out
        vals = sorted(r["rng"] for r in rows)
        med = vals[len(vals) // 2]
        for name, sub in (("compressed", [r for r in rows if r["rng"] <= med]),
                          ("expanded", [r for r in rows if r["rng"] > med])):
            if sub:
                out[name] = dict(n=len(sub), mean_r=sum(x["r"] for x in sub) / len(sub),
                                 median_range_ticks=med)
        return out
    for k in sorted({r[key] for r in rows}):
        sub = [r for r in rows if r[key] == k]
        out[str(k)] = dict(n=len(sub), mean_r=sum(x["r"] for x in sub) / len(sub))
    return out


def decide(primary, placebos, gates_ok):
    """La etiqueta la emite esta funcion, no la narrativa.

    PRERANGE_EDGE exige TRES cosas simultaneas:
      1. IC95 HAC estrictamente > 0 (efecto)
      2. familia de placebos suficiente (piso de p_perm <= 0.05)
      3. rank 1: la ventana elegida a ojo le gana a TODOS los placebos
    Si (1) se cumple pero (2) o (3) no, la etiqueta es WINDOW_UNSPECIFIC: hay
    reversion, pero no es propiedad de ESTA ventana.
    """
    ic = primary["ic"]
    means = [p["ic"]["mean"] for p in placebos if p["ic"]["mean"] is not None]
    p_perm = None
    if means and ic["mean"] is not None:
        rank = 1 + sum(1 for m in means if m >= ic["mean"])
        p_perm = rank / (len(means) + 1)
    if not gates_ok or ic["abstain_inferencia"]:
        return "PRERANGE_UNDERPOWERED", p_perm
    if ic["ci95_upper"] is not None and ic["ci95_upper"] < 0:
        return "PRERANGE_FADE", p_perm
    if ic["ci95_lower"] is not None and ic["ci95_lower"] > 0:
        family_ok = len(means) >= MIN_USABLE_PLACEBOS
        rank_1 = p_perm is not None and p_perm <= 1.0 / (len(means) + 1)
        if family_ok and rank_1:
            return "PRERANGE_EDGE", p_perm
        return "PRERANGE_WINDOW_UNSPECIFIC", p_perm
    return "PRERANGE_NO_EDGE", p_perm


def apply_provenance_cap(label, window_provenance):
    """Techo de etiqueta por procedencia de la ventana.

    Si la ventana se eligio mirando ESTOS datos (o no se sabe de donde salio),
    PRERANGE_EDGE no es emitible: el rank contra los placebos ya estaba
    comprometido por la seleccion. El cap solo BAJA etiquetas, nunca las sube.
    """
    if label == "PRERANGE_EDGE" and window_provenance not in PROVENANCE_ALLOWING_EDGE:
        return "PRERANGE_WINDOW_UNSPECIFIC", True
    return label, False


def run(m1_csv, tick, asset="UNKNOWN", start_min=PRIMARY_START_MIN,
        dur_min=WINDOW_DUR_MIN, d_frac=D_FRAC, out_path=None,
        window_provenance="unknown", macro_dates=None):
    bars = load_m1(m1_csv, tick)
    sessions = group_sessions(bars)

    primary = run_window(sessions, start_min, dur_min, d_frac)
    placebos = [run_window(sessions, start_min + off, dur_min, d_frac)
                for off in PLACEBO_OFFSETS
                if 0 <= start_min + off and start_min + off + dur_min < SESSION_END_MIN]

    gates = dict(
        sessions_ge_30=primary["n_events"] >= MIN_SESSIONS,
        resolution=primary["frac_resolved"] >= RESOLUTION_MIN,
        ties=primary["frac_tie"] <= TIE_FRAC_MAX,
        coverage=primary["coverage"] >= COVERAGE_MIN,
    )
    label, p_perm = decide(primary, placebos, all(gates.values()))
    label, cap_applied = apply_provenance_cap(label, window_provenance)
    n_usable = sum(1 for p in placebos if p["ic"]["mean"] is not None)

    # estratos estructurales de la familia (declarados a priori)
    strata = {}
    for p in placebos:
        strata.setdefault(classify_window(p["start_min"], dur_min), []).append(p)
    strata_out = {}
    for name, group in strata.items():
        ms = [g["ic"]["mean"] for g in group if g["ic"]["mean"] is not None]
        strata_out[name] = dict(
            n_windows=len(group), n_usable=len(ms),
            mean_of_means=(sum(ms) / len(ms)) if ms else None,
            starts=[g["start_hhmm"] for g in group],
        )

    # El confusor macro NO se resuelve con placebos (ver LEMA): se resuelve
    # partiendo la propia ventana primaria por dia con/sin evento programado.
    macro_split = None
    if macro_dates:
        rr = primary["rows"]
        no_m = [r["r"] for r in rr if r["date"] not in macro_dates]
        wi_m = [r["r"] for r in rr if r["date"] in macro_dates]
        macro_split = dict(n_macro=len(wi_m), n_no_macro=len(no_m),
                           ic_macro=hac_bartlett_ci(wi_m),
                           ic_no_macro=hac_bartlett_ci(no_m))

    payload = dict(
        schema_version=SCHEMA_VERSION,
        asset=asset, tick_size=tick,
        label=label,
        window=dict(start=primary["start_hhmm"], duration_min=dur_min,
                    d_frac=d_frac, horizon_end_min=SESSION_END_MIN),
        primary={k: v for k, v in primary.items() if k != "rows"},
        placebo_permutation=dict(
            n_placebos=len(placebos),
            n_usable=n_usable,
            min_usable_required=MIN_USABLE_PLACEBOS,
            family_ok=n_usable >= MIN_USABLE_PLACEBOS,
            p_perm_floor=(1.0 / (n_usable + 1)) if n_usable else None,
            p_perm=p_perm,
            means={p["start_hhmm"]: p["ic"]["mean"] for p in placebos},
            n_events={p["start_hhmm"]: p["n_events"] for p in placebos},
        ),
        descriptive=dict(
            by_range=stratify(primary["rows"], "range_median"),
            by_weekday=stratify(primary["rows"], "weekday"),
            by_second_side=stratify(primary["rows"], "second_side"),
        ),
        gates=gates,
        n_sessions_total=len(sessions),
        window_provenance=window_provenance,
        label_cap_applied=cap_applied,
        placebo_strata=strata_out,
        identification=dict(
            primary_stratum=classify_window(start_min, dur_min),
            no_placebo_contains_0830=all(
                classify_window(p["start_min"], dur_min) != "contains_0830_macro"
                for p in placebos),
            macro_split=macro_split,
        ),
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
    )
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    payload["payload_sha256"] = hashlib.sha256(raw).hexdigest()
    if out_path:
        Path(out_path).write_text(json.dumps(payload, indent=2, default=str), "utf-8")
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("m1_csv")
    ap.add_argument("--tick", type=float, required=True)
    ap.add_argument("--asset", default="UNKNOWN")
    ap.add_argument("--start-min", type=int, default=PRIMARY_START_MIN)
    ap.add_argument("--duration", type=int, default=WINDOW_DUR_MIN)
    ap.add_argument("--d-frac", type=float, default=D_FRAC)
    ap.add_argument("--out", default=None)
    ap.add_argument("--window-provenance", default="unknown",
                    choices=["a_priori_external", "a_priori_mechanism",
                             "chosen_from_this_data", "unknown"])
    ap.add_argument("--macro-dates", default=None,
                    help="CSV/txt con una fecha YYYY-MM-DD por linea: dias con evento programado")
    a = ap.parse_args()
    md = load_macro_dates(a.macro_dates) if a.macro_dates else None
    print(json.dumps(run(a.m1_csv, a.tick, a.asset, a.start_min, a.duration,
                         a.d_frac, a.out, a.window_provenance, md),
                     indent=2, default=str))


if __name__ == "__main__":
    main()
