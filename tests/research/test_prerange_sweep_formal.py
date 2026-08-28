# -*- coding: utf-8 -*-
"""Tests sinteticos del runner PreRange. Falsacion antes de datos reales.

La propiedad critica: bajo random walk sin drift la carrera es simetrica por
construccion, asi que el estimando debe dar ~0 SIN simular brownianos ni
estimar volatilidad. Si eso no se cumple, el estimando esta sesgado y no
sirve para nada.

Correr: python3 tests/research/test_prerange_sweep_formal.py
"""
from __future__ import annotations

import math
import random
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "diag" / "tasa_senales"))
import prerange_sweep_formal as M

TMP = Path(tempfile.mkdtemp(prefix="prerange_"))
WIN_START = M.PRIMARY_START_MIN          # 492 = 08:12
WIN_END = WIN_START + M.WINDOW_DUR_MIN   # 552 = 09:12
DAY_START = 7 * 60
DAY_END = M.SESSION_END_MIN
FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s  %s" % (name, detail))
        FAILURES.append(name)


# ------------------------------------------------ 1. tick rounding
def test_tick():
    print("\n[1] price_to_tick (half-tick)")
    check("floor(x+0.5) no banker's rounding", M.price_to_tick(0.5, 1.0) == 1,
          "got %s, round() daria 0" % M.price_to_tick(0.5, 1.0))
    check("1.5 -> 2", M.price_to_tick(1.5, 1.0) == 2)
    check("6E 1.16785/5e-5", M.price_to_tick(1.16785, 5e-5) == 23357)
    check("negativo estable", M.price_to_tick(-0.5, 1.0) == 0)


# ------------------------------------------------ 2. simetria del estimando
def test_race_symmetry():
    print("\n[2] reversion_race: simetria y categorias")

    def ev(bars, side="upper", anchor=1000, rng=10):
        post = [dict(hi=anchor, lo=anchor, cl=anchor)] + bars
        return dict(idx=0, post=post, rng=rng, anchor=anchor, second_side=side)

    # d = 10 * 0.5 = 5 -> revert=995, cont=1005 (barrido arriba)
    r, c = M.reversion_race(ev([dict(hi=1000, lo=990, cl=995)]))
    check("revierte primero -> +1", (r, c) == (1.0, "revert_first"), str((r, c)))

    r, c = M.reversion_race(ev([dict(hi=1010, lo=1000, cl=1006)]))
    check("continua primero -> -1", (r, c) == (-1.0, "cont_first"), str((r, c)))

    r, c = M.reversion_race(ev([dict(hi=1010, lo=990, cl=1000)]))
    check("misma barra -> empate 0", (r, c) == (0.0, "tie_same_bar"), str((r, c)))

    r, c = M.reversion_race(ev([dict(hi=1002, lo=998, cl=1000)]))
    check("nadie toca -> censura 0", (r, c) == (0.0, "double_censor"), str((r, c)))

    # espejo: barrido abajo debe dar el resultado espejado con precios espejados
    r_up, _ = M.reversion_race(ev([dict(hi=1000, lo=990, cl=995)], side="upper"))
    r_dn, _ = M.reversion_race(ev([dict(hi=1010, lo=1000, cl=1005)], side="lower"))
    check("espejo exacto arriba/abajo", r_up == r_dn == 1.0, "%s vs %s" % (r_up, r_dn))

    # niveles equidistantes del anchor: el sesgo que mataria el test
    d = int(round(10 * M.D_FRAC))
    check("revert y cont equidistantes del anchor", (1000 - (1000 - d)) == ((1000 + d) - 1000))


# ------------------------------------------------ 3. HAC
def test_hac():
    print("\n[3] HAC Bartlett")
    vals = [1.0, -1.0] * 20
    got = M.hac_bartlett_ci(vals)
    n = len(vals)
    mean = sum(vals) / n
    L = max(1, math.ceil(math.sqrt(n)))
    dv = [v - mean for v in vals]
    var = sum(t * t for t in dv) / n
    for k in range(1, L + 1):
        g = sum(dv[t] * dv[t - k] for t in range(k, n)) / n
        var += 2.0 * (1.0 - k / (L + 1)) * g
    se = math.sqrt(max(var / n, 0.0))
    check("media", abs(got["mean"] - mean) < 1e-12)
    check("se_hac replicable a mano", abs(got["se_hac"] - se) < 1e-12,
          "%s vs %s" % (got["se_hac"], se))
    check("lag = ceil(sqrt(n))", got["lag"] == L)
    check("IC = mean +/- 1.96*se",
          abs(got["ci95_upper"] - (mean + 1.96 * se)) < 1e-12)
    check("n<30 -> abstain", M.hac_bartlett_ci([1.0] * 10)["abstain_inferencia"] is True)


# ------------------------------------------------ 4. generador sintetico
def gen_bars(rng, p0=40000, subs=10):
    bars = []
    price = p0
    for mod in range(DAY_START, DAY_END + 1):
        sub = [price]
        for _ in range(subs):
            price += rng.choice([-1, 1])
            sub.append(price)
        bars.append(dict(mod=mod, hi=max(sub), lo=min(sub), cl=price))
    return bars


def plant(bars, rng, direction, bias=0.5):
    """direction=+1 planta reversion, -1 planta continuacion."""
    win = [b for b in bars if WIN_START <= b["mod"] < WIN_END]
    w_hi, w_lo = max(b["hi"] for b in win), min(b["lo"] for b in win)
    post = [b for b in bars if WIN_END <= b["mod"] <= DAY_END]
    first = second_i = second_side = None
    for i, b in enumerate(post):
        up, dn = b["hi"] >= w_hi, b["lo"] <= w_lo
        if first is None:
            if up and dn:
                return bars
            if up:
                first = "upper"
            elif dn:
                first = "lower"
            continue
        if (first == "upper" and dn) or (first == "lower" and up):
            second_i = i
            second_side = "lower" if first == "upper" else "upper"
            break
    if second_i is None:
        return bars
    rev_dir = -1 if second_side == "upper" else 1
    drift = rev_dir * direction
    price = post[second_i]["cl"]
    for j in range(second_i + 1, len(post)):
        sub = [price]
        for _ in range(10):
            step = drift if rng.random() < bias else rng.choice([-1, 1])
            price += step
            sub.append(price)
        post[j].update(hi=max(sub), lo=min(sub), cl=price)
    return bars


def write_csv(name, n_sessions, seed, direction=0, bias=0.5):
    rng = random.Random(seed)
    lines = ["Time,Open,High,Low,Close"]
    d = datetime(2025, 1, 6)
    made = 0
    while made < n_sessions:
        if d.weekday() < 5:
            bars = gen_bars(rng)
            if direction != 0:
                bars = plant(bars, rng, direction, bias)
            for b in bars:
                t = d + timedelta(minutes=b["mod"])
                lines.append("%s,%d,%d,%d,%d" % (
                    t.strftime("%Y-%m-%d %H:%M:%S"), b["cl"], b["hi"], b["lo"], b["cl"]))
            made += 1
        d += timedelta(days=1)
    path = TMP / name
    path.write_text("\n".join(lines), "utf-8")
    return str(path)


# ------------------------------------------------ 5. nulo
def test_null():
    print("\n[4] NULO: random walk -> estimando ~0 sin simular nada")
    p = write_csv("_syn_null.csv", 160, seed=20260814)
    out = M.run(p, tick=1.0, asset="SYN_NULL")
    pr = out["primary"]
    ic = pr["ic"]
    print("    n_events=%s coverage=%.3f mean=%+.4f IC=[%+.3f,%+.3f] p_rev=%.3f label=%s"
          % (pr["n_events"], pr["coverage"], ic["mean"], ic["ci95_lower"],
             ic["ci95_upper"], pr["p_revert_over_decided"] or -1, out["label"]))
    check("IC cruza cero en el nulo", ic["ci95_lower"] < 0 < ic["ci95_upper"],
          "IC=[%.3f,%.3f]" % (ic["ci95_lower"], ic["ci95_upper"]))
    check("label no reclama edge",
          out["label"] in ("PRERANGE_NO_EDGE", "PRERANGE_UNDERPOWERED"), out["label"])
    check("P(revierte|decidido) ~ 0.5",
          abs((pr["p_revert_over_decided"] or 0) - 0.5) < 0.12,
          str(pr["p_revert_over_decided"]))
    check("tasa de doble barrido alta (la tautologia)", pr["coverage"] > 0.5,
          "%.3f" % pr["coverage"])
    check("pnl no accedido", out["pnl_accessed"] is False)
    return out


# ------------------------------------------------ 6. efectos plantados
def test_planted():
    print("\n[5] REVERSION plantada -> mean>0")
    p = write_csv("_syn_rev.csv", 140, seed=777, direction=+1, bias=0.45)
    out = M.run(p, tick=1.0, asset="SYN_REV")
    ic = out["primary"]["ic"]
    print("    mean=%+.4f IC=[%+.3f,%+.3f] p_perm=%s label=%s"
          % (ic["mean"], ic["ci95_lower"], ic["ci95_upper"],
             out["placebo_permutation"]["p_perm"], out["label"]))
    check("detecta reversion (mean>0)", ic["mean"] > 0, str(ic["mean"]))
    check("IC excluye cero por arriba", ic["ci95_lower"] > 0,
          "IC=[%.3f,%.3f]" % (ic["ci95_lower"], ic["ci95_upper"]))
    # La sesion sintetica es 07:00-16:00, asi que solo 11 de 25 placebos tienen
    # datos y el piso de p_perm queda en 0.083 > 0.05. Aun con el efecto
    # plantado, el runner NO debe reclamar PRERANGE_EDGE: la ventana no pudo
    # ser distinguida de sus placebos con la resolucion disponible.
    check("con familia insuficiente NO reclama EDGE",
          out["label"] == "PRERANGE_WINDOW_UNSPECIFIC", out["label"])
    check("family_ok=False reportado",
          out["placebo_permutation"]["family_ok"] is False)

    print("\n[6] CONTINUACION plantada -> mean<0 (FADE)")
    p = write_csv("_syn_cont.csv", 140, seed=888, direction=-1, bias=0.45)
    out2 = M.run(p, tick=1.0, asset="SYN_CONT")
    ic2 = out2["primary"]["ic"]
    print("    mean=%+.4f IC=[%+.3f,%+.3f] label=%s"
          % (ic2["mean"], ic2["ci95_lower"], ic2["ci95_upper"], out2["label"]))
    check("detecta continuacion (mean<0)", ic2["mean"] < 0, str(ic2["mean"]))
    check("label FADE", out2["label"] == "PRERANGE_FADE", out2["label"])
    return out


# ------------------------------------------------ 7. placebos y gates
def test_placebos_and_gates(null_out):
    print("\n[7] Familia de placebos y piso de p_perm")
    k = null_out["placebo_permutation"]["n_placebos"]
    usable = sum(1 for v in null_out["placebo_permutation"]["means"].values() if v is not None)
    floor = null_out["placebo_permutation"]["p_perm_floor"]
    print("    placebos declarados=%s con datos=%s piso_p_perm=%.4f requeridos=%s"
          % (k, usable, floor, M.MIN_USABLE_PLACEBOS))
    check("piso de p_perm reportado explicitamente", floor is not None)
    check("gate de familia coherente con el piso",
          null_out["placebo_permutation"]["family_ok"] == (floor <= 0.05),
          "family_ok=%s piso=%.4f" % (null_out["placebo_permutation"]["family_ok"], floor))
    check("19 placebos requeridos -> piso 0.05",
          abs(1.0 / (M.MIN_USABLE_PLACEBOS + 1) - 0.05) < 1e-12)
    check("grilla declarada alcanza el minimo en datos 24h",
          k >= M.MIN_USABLE_PLACEBOS, "declarados=%s" % k)
    check("ventana primaria excluida de sus placebos",
          null_out["window"]["start"] not in null_out["placebo_permutation"]["means"])
    check("placebos sin datos no contaminan (mean=None ignorado)", usable <= k)
    check("ningun placebo se solapa con la ventana primaria",
          all(abs(o) >= M.WINDOW_DUR_MIN for o in M.PLACEBO_OFFSETS))

    print("\n[8] Gates y trazabilidad")
    check("gates presentes", set(null_out["gates"]) ==
          {"sessions_ge_30", "resolution", "ties", "coverage"}, str(null_out["gates"]))
    check("sha256 del payload", len(null_out["payload_sha256"]) == 64)
    check("holdout no incluido", null_out["holdout_included"] is False)
    check("descriptivos presentes (no adjudican)",
          set(null_out["descriptive"]) == {"by_range", "by_weekday", "by_second_side"})

    print("\n[9] Datos insuficientes -> UNDERPOWERED, nunca edge")
    p = write_csv("_syn_tiny.csv", 12, seed=5)
    tiny = M.run(p, tick=1.0, asset="SYN_TINY")
    print("    n_events=%s label=%s" % (tiny["primary"]["n_events"], tiny["label"]))
    check("pocas sesiones -> UNDERPOWERED",
          tiny["label"] == "PRERANGE_UNDERPOWERED", tiny["label"])


# ------------------------------------------------ 8. procedencia (techo de etiqueta)
def test_provenance_cap():
    print("\n[10] Procedencia de la ventana: techo de etiqueta")
    for prov in ("unknown", "chosen_from_this_data"):
        lab, cap = M.apply_provenance_cap("PRERANGE_EDGE", prov)
        check("%s degrada EDGE" % prov,
              lab == "PRERANGE_WINDOW_UNSPECIFIC" and cap is True, "%s/%s" % (lab, cap))
    for prov in ("a_priori_external", "a_priori_mechanism"):
        lab, cap = M.apply_provenance_cap("PRERANGE_EDGE", prov)
        check("%s permite EDGE" % prov,
              lab == "PRERANGE_EDGE" and cap is False, "%s/%s" % (lab, cap))
    for lab0 in ("PRERANGE_NO_EDGE", "PRERANGE_FADE", "PRERANGE_UNDERPOWERED",
                 "PRERANGE_WINDOW_UNSPECIFIC"):
        lab, cap = M.apply_provenance_cap(lab0, "a_priori_external")
        check("el cap nunca sube %s" % lab0, lab == lab0 and cap is False)
    check("'unknown' no habilita EDGE", "unknown" not in M.PROVENANCE_ALLOWING_EDGE)
    check("'chosen_from_this_data' no habilita EDGE",
          "chosen_from_this_data" not in M.PROVENANCE_ALLOWING_EDGE)


# ------------------------------------------------ 9. lema de identificacion
def test_identification_lemma():
    print("\n[11] LEMA: ningun placebo puede contener las 08:30")
    prim = M.classify_window(M.PRIMARY_START_MIN)
    check("la ventana primaria contiene el dato de 08:30",
          prim == "contains_0830_macro", prim)
    offenders = [o for o in M.PLACEBO_OFFSETS
                 if M.classify_window(M.PRIMARY_START_MIN + o) == "contains_0830_macro"]
    check("ningun placebo contiene 08:30", offenders == [], str(offenders))
    # y no es casualidad de la grilla elegida: es geometrico
    starts = [s for s in range(0, M.SESSION_END_MIN)
              if M.classify_window(s) == "contains_0830_macro"]
    check("TODA ventana que contiene 08:30 se solapa con la primaria",
          all(abs(s - M.PRIMARY_START_MIN) < M.WINDOW_DUR_MIN for s in starts),
          "%s..%s" % (starts[0], starts[-1]))
    check("=> los placebos NO pueden identificar el confusor macro",
          offenders == [] and prim == "contains_0830_macro")
    strata = {M.classify_window(M.PRIMARY_START_MIN + o) for o in M.PLACEBO_OFFSETS}
    check("estratos de la familia declarados",
          strata <= {"overnight", "rth_quiet", "contains_0930_cash_open"}, str(strata))
    check("la familia incluye la apertura del cash como estrato aparte",
          "contains_0930_cash_open" in strata, str(strata))


# ------------------------------------------------ 10. split macro (identificacion correcta)
def test_macro_split():
    print("\n[12] Split por dia con/sin evento macro")
    p = write_csv("_syn_macro.csv", 160, seed=20260814)
    dates = sorted({ln.split(",")[0][:10]
                    for ln in Path(p).read_text(encoding="utf-8").splitlines()[1:]})
    mp = TMP / "_macro_dates.csv"
    mp.write_text("\n".join(dates[::2]), "utf-8")
    md = M.load_macro_dates(str(mp))
    check("fechas macro parseadas", len(md) == len(dates[::2]),
          "%s vs %s" % (len(md), len(dates[::2])))
    out = M.run(p, tick=1.0, asset="SYN_MACRO", macro_dates=md)
    ms = out["identification"]["macro_split"]
    print("    n_macro=%s n_no_macro=%s" % (ms["n_macro"], ms["n_no_macro"]))
    check("el split suma el total de eventos",
          ms["n_macro"] + ms["n_no_macro"] == out["primary"]["n_events"],
          "%s+%s vs %s" % (ms["n_macro"], ms["n_no_macro"], out["primary"]["n_events"]))
    check("el subset SIN macro tiene su propio IC HAC", "ci95_lower" in ms["ic_no_macro"])
    check("el subset CON macro tiene su propio IC HAC", "ci95_lower" in ms["ic_macro"])
    check("sin --macro-dates el split es None",
          M.run(p, tick=1.0)["identification"]["macro_split"] is None)
    check("el lema queda registrado en el payload",
          out["identification"]["no_placebo_contains_0830"] is True)
    check("estrato de la primaria en el payload",
          out["identification"]["primary_stratum"] == "contains_0830_macro")
    check("placebo_strata reportado por estrato",
          set(out["placebo_strata"]) <= {"overnight", "rth_quiet",
                                         "contains_0930_cash_open"},
          str(set(out["placebo_strata"])))
    check("provenance por defecto = unknown (se asume lo peor)",
          out["window_provenance"] == "unknown", out["window_provenance"])


if __name__ == "__main__":
    test_tick()
    test_race_symmetry()
    test_hac()
    null_out = test_null()
    test_planted()
    test_placebos_and_gates(null_out)
    test_provenance_cap()
    test_identification_lemma()
    test_macro_split()
    print("\n" + "=" * 60)
    if FAILURES:
        print("FALLARON %d test(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("TODOS LOS TESTS PASARON")
