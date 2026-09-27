"""EspejoImpulsos — impulsos que el mercado recorrió sin estar «listo» y su vuelta en espejo.

Kernel **target-free y causal** de la familia ESPEJO-IND (registro y OK de Nico:
`docs/research/REGISTRO_FAMILIA_ESPEJO_IND_20260926.md` §3 y §5; atributos de «zona no lista» en §6).

## Qué marca

1. **Impulso A→B** con el detector de `tools/espejo_macro.py::detect_var` (portado sin cambios de lógica), con
   eficiencia mínima baja (e_min = 0,3) para que el censo contenga eficientes **e** ineficientes.
   - B se confirma cuando el retroceso desde B llega a r·W (A1).
   - Los impulsos cerrados por tiempo (`why == 2`) quedan en el censo como `IMP_UNCONFIRMED`.
2. **Etiquetas del impulso** (se guardan, nunca filtran):
   - I1 eficiencia en [e_min, e_max);
   - I2 volumen por tick por debajo del percentil 33 de los impulsos de sesiones anteriores;
   - `ineficiente = I1 ∨ I2`.
3. **«Zona no lista»** (pedido de Nico, 27/09): el tramo de precio que el impulso cruzó casi sin volumen.
   - Se toma del perfil de volumen del impulso: el tramo contiguo más ancho cuya densidad queda por debajo del 25 % de
     la mediana.
   - Se reporta también la «aceptación en B»: cuánto volumen negoció el precio cerca de B (dentro de 0,25·W) desde B
     hasta el candidato, relativo al volumen del impulso. Es la pregunta «¿ya resolvió comercio en otra área?».
4. **Vuelta**: estados `MIRROR_CANDIDATE` (x = 0,25), `MIRROR_PROGRESS` (0,5 y 0,75), `MIRROR_COMPLETED` (toca A),
   `MIRROR_FAILED` (extremo nuevo más allá de B), `MIRROR_EXPIRED` (horizonte 3 × duración, o fin de sesión) e
   `IMP_NO_MIRROR`. Nada emitido se reescribe.
5. **Semejanza** de la vuelta con el tramo espejo: componentes `vel`, `efi`, `forma` y `ondas` de
   `tools/espejo_semejanza.py::eventos`, con percentil contra eventos de **sesiones anteriores** y la marca S2
   (`vel` y `forma` ≥ mediana).

## Causalidad

- Cada evento lleva `bar`, la vela a cuyo cierre se conoce. Cortar la serie en j no cambia ningún evento con
  `bar < j`: está en los tests.
- El fin de sesión lo da el calendario (`last_of_session`), no el final del arreglo. Una serie cortada a mitad de
  sesión deja los estados abiertos, sin inventar un vencimiento.

## Qué NO decide

No mide si hay espejo más seguido que el azar ni si paga. Eso es campaña, con pre-registro y el STOP del proyecto.
"""
from __future__ import annotations

import math

import numpy as np

NAME = "EspejoImpulsos"
VERSION = "1.0"

RESEARCH_DEFAULTS = dict(
    max_bars=20,          # 25t: configuración de Nico en TBZX
    min_w=17.0,           # ticks; en modo ATR se ignora
    atr_k=None,           # velas de tiempo: 3 → umbral 3·ATR(14) cerrado en la vela anterior
    atr_n=14,
    e_min=0.3,
    e_max=0.6,            # I1: eficiencia en [e_min, e_max)
    retr=0.3,             # A1
    xs=(0.25, 0.5, 0.75),
    horizon_mult=3.0,
    gap_reset_s=1800.0,
    i2_pct=33.3,
    ref_min=30,           # eventos previos mínimos para dar percentiles
    thin_frac=0.25,       # «no lista»: densidad < 25 % de la mediana del perfil
    accept_band=0.25,     # aceptación en B: banda de 0,25·W desde B
    npts=20,
)
FINAL = ("MIRROR_COMPLETED", "MIRROR_FAILED", "MIRROR_EXPIRED", "IMP_NO_MIRROR", "IMP_UNCONFIRMED")
COMP = ("vel", "efi", "forma", "ondas")
COMP2 = ("sim_vel", "sim_t", "sim_v")


def params_of(overrides=None):
    p = dict(RESEARCH_DEFAULTS)
    if overrides:
        p.update({k: v for k, v in overrides.items() if v is not None})
    return p


# ------------------------------------------------------------------ detector (port de detect_var)
def atr_prev(H, L, C, n=14):
    """ATR(n) simple cerrado en la vela ANTERIOR (causal). inf hasta tener n velas."""
    pc = np.r_[C[0], C[:-1]]
    tr = np.maximum(H - L, np.maximum(np.abs(H - pc), np.abs(L - pc)))
    cs = np.r_[0.0, np.cumsum(tr)]
    out = np.full(len(C), np.inf)
    for j in range(n + 1, len(C)):
        out[j] = (cs[j] - cs[j - n]) / n
    return out


def detect(t, H, L, C, V, thr_arr, p):
    """Port literal de `tools/espejo_macro.py::detect_var` (más el volumen del impulso). Devuelve dicts con
    d, a, ext, i0, iext, jconf, why, vol. `why == 1`: confirmado por retroceso; `why == 2`: cerrado por tiempo."""
    W, e0, r = int(p["max_bars"]), float(p["e_min"]), float(p["retr"])
    n = len(C)
    path = np.r_[0.0, np.cumsum(np.abs(np.diff(C)))] if n else np.zeros(0)
    out = []
    active = False
    floorI = 0
    d = 0; i0 = 0; a = 0.0; ext = 0.0; iext = 0; thr_t = 0.0
    for j in range(W, n):
        if t[j] - t[j - 1] > p["gap_reset_s"]:
            active = False
        if not active:
            w0 = max(j - W, floorI)
            if w0 >= j:
                continue
            thr = max(thr_arr[j], 2.0)
            if not thr < 1e17:
                continue
            ia = w0 + int(np.argmin(L[w0:j + 1])); ib = w0 + int(np.argmax(H[w0:j + 1]))
            found = False; bnet = 0.0
            if ia < j:
                net = C[j] - L[ia]; pp = path[j] - path[ia]
                if net >= thr and pp > 0 and (C[j] - C[ia]) / pp >= e0:
                    found = True; bnet = net; d = 1; i0 = ia; a = L[ia]; ext = H[j]
            if ib < j:
                net2 = H[ib] - C[j]; pp2 = path[j] - path[ib]
                if net2 >= thr and pp2 > 0 and (C[ib] - C[j]) / pp2 >= e0 and ((not found) or net2 > bnet):
                    found = True; d = -1; i0 = ib; a = H[ib]; ext = L[j]
            if found:
                active = True; iext = j; thr_t = thr
            continue
        if d == 1 and H[j] > ext:
            ext = H[j]; iext = j
        elif d == -1 and L[j] < ext:
            ext = L[j]; iext = j
        tot = abs(ext - a)
        retr = (ext - L[j]) if d == 1 else (H[j] - ext)
        why = 1 if retr >= max(2.0, r * tot) else (2 if j - i0 >= W else 0)
        if why == 0:
            continue
        if tot >= thr_t:
            pp = path[iext] - path[i0]
            out.append(dict(d=d, a=float(a), ext=float(ext), i0=i0, iext=iext, jconf=j, why=why, thr=float(thr_t),
                            eff=float(abs(C[iext] - C[i0]) / pp) if pp > 0 else 1.0,
                            vol=float(V[i0:iext + 1].sum())))
        floorI = iext
        active = False
    return out


# ------------------------------------------------------------------ atributos «zona no lista»
def perfil_no_lista(H, L, V, i0, iext, a, ext, p):
    """Perfil de volumen del impulso (volumen de cada vela repartido parejo en su rango, recortado a [A, B]).
    Devuelve el tramo contiguo más ancho con densidad < thin_frac·mediana: (lo, hi, fraccion_de_W)."""
    lo_p, hi_p = min(a, ext), max(a, ext)
    nb = int(max(1, round(hi_p - lo_p)))
    edges = np.linspace(lo_p, hi_p, nb + 1)
    dens = np.zeros(nb)
    for q in range(i0, iext + 1):
        l, h = max(L[q], lo_p), min(H[q], hi_p)
        if h < l:
            continue
        span = max(h - l, 1e-9)
        ov = np.clip(np.minimum(edges[1:], h) - np.maximum(edges[:-1], l), 0, None)
        if h == l:
            k = min(int((l - lo_p) / (hi_p - lo_p) * nb), nb - 1) if hi_p > lo_p else 0
            dens[k] += V[q]
        else:
            dens += V[q] * ov / span
    med = float(np.median(dens)) if nb else 0.0
    thin = dens < p["thin_frac"] * med if med > 0 else np.zeros(nb, bool)
    best = (0, -1); k = 0
    while k < nb:
        if thin[k]:
            s = k
            while k < nb and thin[k]:
                k += 1
            if k - s > best[1] - best[0] + 1:
                best = (s, k - 1)
        else:
            k += 1
    if best[1] < best[0]:
        return None, None, 0.0
    lo, hi = float(edges[best[0]]), float(edges[best[1] + 1])
    return lo, hi, (hi - lo) / (hi_p - lo_p) if hi_p > lo_p else 0.0


def aceptacion_B(H, L, V, iext, k, ext, W, d, p):
    """Volumen negociado en la banda de accept_band·W junto a B, desde B hasta la vela k (incluida)."""
    band_lo, band_hi = (ext - p["accept_band"] * W, ext) if d == 1 else (ext, ext + p["accept_band"] * W)
    tot = 0.0; velas = 0
    for q in range(iext, k + 1):
        l, h = L[q], H[q]
        ov = min(h, band_hi) - max(l, band_lo)
        if ov < 0:
            continue
        velas += 1
        tot += V[q] * (ov / (h - l) if h > l else 1.0)
    return tot, velas


# ------------------------------------------------------------------ semejanza (componentes de espejo_semejanza)
def _zigzag(y, thr):
    if len(y) < 2:
        return 0
    n = 0; dirn = 0; ext = y[0]
    for v in y[1:]:
        if dirn >= 0:
            if v > ext:
                ext = v
            elif ext - v >= thr:
                if dirn == 1:
                    n += 1
                dirn = -1; ext = v
            if dirn == 0 and v - y[0] >= thr:
                dirn = 1
        else:
            if v < ext:
                ext = v
            elif v - ext >= thr:
                n += 1; dirn = 1; ext = v
    return n


def _norm(y, npts):
    return np.interp(np.linspace(0, 1, npts), np.linspace(0, 1, len(y)), y)


def _tramo_espejo(C, imp, f):
    """Última vela del impulso con avance (por cierres) ≤ 1 − f: desde ahí hasta B está el tramo que la vuelta espeja."""
    d, a, ext, i0, iext = imp["d"], imp["a"], imp["ext"], imp["i0"], imp["iext"]
    prog = d * (C[i0:iext + 1] - a) / abs(ext - a)
    idx = np.where(prog <= 1 - f)[0]
    return i0 + (int(idx[-1]) if len(idx) else 0)


def semejanza(t, C, imp, k, f, p):
    """Los 4 componentes de `tools/espejo_semejanza.py::eventos` con datos ≤ vela k."""
    d, a, ext, i0, iext = imp["d"], imp["a"], imp["ext"], imp["i0"], imp["iext"]
    W = abs(ext - a)
    m = _tramo_espejo(C, imp, f)
    seg_m = C[m:iext + 1][::-1]; seg_v = C[iext:k + 1]
    dt_m = max(t[iext] - t[m], 1.0); dt_v = max(t[k] - t[iext], 1.0)
    vel = -abs(math.log(max(f * W / dt_v, 1e-12) / (max(abs(ext - C[m]), 1.0) / dt_m)))

    def efi(s):
        pp = np.abs(np.diff(s)).sum()
        return abs(s[-1] - s[0]) / pp if pp > 0 else 1.0
    ym = d * (ext - seg_m) / (f * W); yv = d * (ext - seg_v) / (f * W)
    forma = (-float(np.sqrt(np.mean((_norm(ym, p["npts"]) - _norm(yv, p["npts"])) ** 2)))
             if len(ym) > 1 and len(yv) > 1 else float("nan"))
    ondas = -abs(_zigzag(yv, 0.1 / f) / f - _zigzag(ym, 0.1 / f) / f)
    return dict(vel=float(vel), efi=float(-abs(efi(seg_v) - efi(seg_m))), forma=forma, ondas=float(ondas))


def semejanza_niveles(t, H, L, V, imp, k, f, a0, p):
    """Semejanza v2 (2026-09-27, pedido de Nico: «lo más parecido posible, pero en espejo»), alineada por NIVEL de precio
    en vez de por tiempo normalizado.

    El espejo recorre los mismos niveles que el impulso, en orden inverso. Por eso se comparan, sobre el tramo ya
    retrocedido R = [B − f·W, B] (o su simétrico si el impulso es bajista):
    - `sim_t`: cuánto **tiempo** pasó el precio en cada nivel de R durante el tramo espejo del impulso y durante la
      vuelta. Cada vela reparte su duración pareja en su rango H–L recortado a R. La similitud es el solapamiento de las
      dos distribuciones (1 − ½·L1), en [0, 1]. Si el impulso frenó en un nivel, el espejo también frena ahí.
    - `sim_v`: lo mismo con el **volumen** por nivel. Es la contracara de la «zona no lista»: si el impulso cruzó un nivel
      casi sin negociar, el espejo lo cruza igual.
    - `sim_vel`: exp(−|log(duración de la vuelta / duración del tramo espejo)|), en [0, 1]. Recorren la misma distancia
      f·W, así que es el cociente de velocidades.
    - `sim_abs`: promedio de `sim_vel` y `sim_t`, en [0, 1]. Es absoluta, no depende de una referencia. `sim_v` queda
      fuera del promedio porque en ES a 5 min correlaciona 0,87–0,95 con `sim_t` (diagnóstico del 27/09); se guarda como
      atributo.

    Usa H y L de cada vela, no sólo los cierres, así que tiene sentido aunque la vuelta dure una o dos velas. La forma
    v1, que compara caminos de cierres, con dos puntos no mide nada."""
    d, a, ext, i0, iext = imp["d"], imp["a"], imp["ext"], imp["i0"], imp["iext"]
    W = abs(ext - a)
    m = imp["m"]                                   # tramo espejo: el mismo de v1 (`_tramo_espejo`)
    lo, hi = (ext - f * W, ext) if d == 1 else (ext, ext + f * W)
    nb = int(max(1, min(p["npts"], round(hi - lo))))
    edges = np.linspace(lo, hi, nb + 1)

    def dt(q):
        if q > a0:
            return max(t[q] - t[q - 1], 1e-9)
        return max(t[q + 1] - t[q], 1e-9) if q + 1 < len(t) else 1.0

    def perfil(q0, q1, peso):
        out = np.zeros(nb); dur = 0.0
        for q in range(q0, q1 + 1):
            dur += dt(q)
            l, h = max(L[q], lo), min(H[q], hi)
            if h < l:
                continue
            w = peso(q)
            if h == l:
                j = min(int((l - lo) / (hi - lo) * nb), nb - 1) if hi > lo else 0
                out[j] += w
            else:
                out += w * np.clip(np.minimum(edges[1:], h) - np.maximum(edges[:-1], l), 0, None) / (h - l)
        return out, dur

    def solape(x, y):
        sx, sy = x.sum(), y.sum()
        if sx <= 0 or sy <= 0:
            return float("nan")
        return float(1.0 - 0.5 * np.abs(x / sx - y / sy).sum())
    tm, dur_m = perfil(m, iext, dt); tv, dur_v = perfil(iext + 1, k, dt)
    vm, _ = perfil(m, iext, lambda q: V[q]); vv, _ = perfil(iext + 1, k, lambda q: V[q])
    sim_vel = float(math.exp(-abs(math.log(dur_v / dur_m)))) if dur_m > 0 and dur_v > 0 else float("nan")
    sim_t, sim_v = solape(tm, tv), solape(vm, vv)
    return dict(sim_vel=sim_vel, sim_t=sim_t, sim_v=sim_v,
                sim_abs=float((sim_vel + sim_t) / 2) if sim_vel == sim_vel and sim_t == sim_t else float("nan"),
                velas_vuelta=int(k - iext))


def _pct(v, ref):
    if v != v or len(ref) == 0:
        return float("nan")
    r = np.asarray(ref)
    eq = np.abs(r - v) <= 1e-9                  # empates con tolerancia: log/sqrt pueden diferir en el último ulp
    return float((np.sum((r < v) & ~eq) + 0.5 * np.sum(eq)) / len(r))


# ------------------------------------------------------------------ corrida
def run(t, O, H, L, C, V, session, last_of_session=None, params=None):
    """Corre el kernel sobre velas (precios en ticks). `session`: etiqueta por vela. `last_of_session`: bool por vela,
    True si el calendario dice que es la última de su sesión (si falta, se deduce del cambio de etiqueta, salvo en la
    última vela del arreglo, que queda abierta).

    Devuelve dict(params, impulses, events). Cada impulso termina en exactamente un estado de FINAL o sigue abierto
    (`estado_final = None`) si la serie se corta antes del desenlace."""
    p = params_of(params)
    t = np.asarray(t, float); O = np.asarray(O, float); H = np.asarray(H, float); L = np.asarray(L, float)
    C = np.asarray(C, float); V = np.asarray(V, float); session = np.asarray(session)
    n = len(C)
    if last_of_session is None:
        last_of_session = np.zeros(n, bool)
        if n > 1:
            last_of_session[:-1] = session[1:] != session[:-1]
    last_of_session = np.asarray(last_of_session, bool)
    if p["atr_k"]:
        thr_all = float(p["atr_k"]) * atr_prev(H, L, C, int(p["atr_n"]))
    else:
        thr_all = np.full(n, float(p["min_w"]))
    cuts = np.r_[0, np.where(session[1:] != session[:-1])[0] + 1, n] if n else np.array([0])
    ref_vpt = []                             # V/W de impulsos de sesiones anteriores (I2)
    ref_comp = {x: {c: [] for c in COMP + COMP2} for x in p["xs"]}
    impulses, events = [], []
    for a0, b0 in zip(cuts[:-1], cuts[1:]):
        sl = slice(a0, b0)
        imps = detect(t[sl], H[sl], L[sl], C[sl], V[sl], thr_all[sl], p)
        ses_vpt, ses_comp = [], {x: {c: [] for c in COMP + COMP2} for x in p["xs"]}
        corte_i2 = float(np.percentile(ref_vpt, p["i2_pct"])) if len(ref_vpt) >= p["ref_min"] else None
        for im in imps:
            _procesar(im, a0, b0, t, H, L, C, V, last_of_session, p, corte_i2, ref_comp, ses_comp, impulses, events)
            if im["why"] == 1:
                ses_vpt.append(im["vol"] / abs(im["ext"] - im["a"]))
        ref_vpt += ses_vpt
        for x in p["xs"]:
            for c in COMP + COMP2:
                ref_comp[x][c] += ses_comp[x][c]
    events.sort(key=lambda e: (e["bar"], e["imp_id"], e["seq"]))
    return dict(indicator=NAME, version=VERSION, params=p, impulses=impulses, events=events)


def _procesar(im, a0, b0, t, H, L, C, V, last, p, corte_i2, ref_comp, ses_comp, impulses, events):
    d, a, ext = im["d"], im["a"], im["ext"]
    i0, iext, jc = a0 + im["i0"], a0 + im["iext"], a0 + im["jconf"]
    W = abs(ext - a)
    iid = len(impulses)
    vpt = im["vol"] / W
    I1 = p["e_min"] <= im["eff"] < p["e_max"]
    I2 = None if corte_i2 is None else bool(vpt < corte_i2)
    nl_lo, nl_hi, nl_frac = perfil_no_lista(H, L, V, i0, iext, a, ext, p)
    rec = dict(imp_id=iid, dir=d, A=a, B=ext, W=W, bar_A=i0, bar_B=iext, bar_conf=jc, t_A=float(t[i0]),
               t_B=float(t[iext]), t_conf=float(t[jc]), eff=im["eff"], vol=im["vol"], vol_por_tick=vpt,
               I1=bool(I1), I2=I2, ineficiente=bool(I1 or bool(I2)), no_lista_lo=nl_lo, no_lista_hi=nl_hi,
               no_lista_frac=nl_frac, estado_final=None, bar_final=None)
    impulses.append(rec)
    seq = [0]

    def emit(kind, bar, **kw):
        e = dict(imp_id=iid, kind=kind, bar=int(bar), t=float(t[bar]), seq=seq[0]); e.update(kw)
        seq[0] += 1
        events.append(e)
        if kind in FINAL:
            rec["estado_final"] = kind; rec["bar_final"] = int(bar)

    if im["why"] != 1:
        emit("IMP_UNCONFIRMED", jc)
        return
    emit("IMP_CONFIRMED", jc, dir=d, A=a, B=ext, W=W, ineficiente=rec["ineficiente"],
         no_lista_lo=nl_lo, no_lista_hi=nl_hi)
    horizon = iext + int(math.ceil(p["horizon_mult"] * (iext - i0 + 1)))
    done = set(); candidato = False
    for k in range(iext + 1, b0):
        newext = (d == 1 and H[k] > ext) or (d == -1 and L[k] < ext)
        retr = (ext - L[k]) if d == 1 else (H[k] - ext)
        f = min(max(retr, 0.0) / W, 1.0)
        kk = max(k, jc)                       # nada se sabe antes de confirmar el impulso
        if not newext:
            for x in p["xs"]:
                if x in done or f < x:
                    continue
                done.add(x)
                comp = semejanza(t, C, dict(d=d, a=a, ext=ext, i0=i0, iext=iext), k, f, p)
                pct = {c: _pct(comp[c], ref_comp[x][c]) if len(ref_comp[x][c]) >= p["ref_min"] else float("nan")
                       for c in COMP}
                vals = [v for v in pct.values() if v == v]
                S = float(np.mean(vals)) if len(vals) == len(COMP) else float("nan")
                s2 = bool(pct["vel"] >= 0.5 and pct["forma"] >= 0.5) if pct["vel"] == pct["vel"] and pct["forma"] == pct["forma"] else None
                accV, accN = aceptacion_B(H, L, V, iext, k, ext, W, d, p)
                imp_d = dict(d=d, a=a, ext=ext, i0=i0, iext=iext)
                imp_d["m"] = _tramo_espejo(C, imp_d, f)
                niv = semejanza_niveles(t, H, L, V, imp_d, k, f, a0, p)
                p2 = {c: _pct(niv[c], ref_comp[x][c]) if len(ref_comp[x][c]) >= p["ref_min"] else float("nan") for c in COMP2}
                s2v2 = (bool(p2["sim_vel"] >= 0.5 and p2["sim_t"] >= 0.5)
                        if p2["sim_vel"] == p2["sim_vel"] and p2["sim_t"] == p2["sim_t"] else None)
                for c in COMP:
                    ses_comp[x][c].append(comp[c])
                for c in COMP2:
                    if niv[c] == niv[c]:
                        ses_comp[x][c].append(niv[c])
                emit("MIRROR_CANDIDATE" if not candidato else "MIRROR_PROGRESS", kk, x=x, f=f, **comp,
                     **{f"p_{c}": pct[c] for c in COMP}, S=S, S2=s2,
                     aceptacion_B=accV / im["vol"] if im["vol"] > 0 else float("nan"), velas_en_B=accN,
                     **niv, **{f"p_{c}": p2[c] for c in COMP2}, S2v2=s2v2, forma_fiable=bool(niv["velas_vuelta"] >= 3))
                candidato = True
        if newext:
            emit("MIRROR_FAILED" if candidato else "IMP_NO_MIRROR", kk, reason="new_extreme")
            return
        if candidato and f >= 1.0:
            far = (a - L[k]) if d == 1 else (H[k] - a)
            emit("MIRROR_COMPLETED", kk, sobrepaso_W=max(far, 0.0) / W, velas=k - iext)
            return
        if k >= horizon or last[k]:
            reason = "horizon" if k >= horizon else "session_end"
            emit("MIRROR_EXPIRED" if candidato else "IMP_NO_MIRROR", kk, reason=reason)
            return
    if iext + 1 >= b0 and last[b0 - 1]:       # el impulso terminó en la última vela de la sesión: no hay vuelta
        emit("IMP_NO_MIRROR", max(b0 - 1, jc), reason="session_end")
