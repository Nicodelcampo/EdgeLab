"""AACloseOpenDiffs — gaps close→open entre velas M1, con confluencia al nacer.

Port del `.cs` homónimo. Lo distintivo, y la razón por la que entra al bridge:
**todo se computa sobre una subserie de 1 MINUTO**, no sobre las barras del chart
primario. El `.cs` hace `AddDataSeries(BarsPeriodType.Minute, 1)` y descarta todo
lo que no sea `BarsInProgress == 1`.

Consecuencia fuerte para la paridad: **la salida NO depende del `bar_spec` del
chart**. El mismo conjunto de zonas sale en `time:1`, `tick:25` o `tick:10`. Es
la primera vez que un kernel del proyecto tiene esa propiedad, y está fijada como
test (`tests/bridge/test_aacloseopendiffs.py`).

DEFINICIÓN DEL EVENTO (`.cs` L207-211)
    gap = |close(M1 anterior) − open(M1 actual)|
    se registra si  gap >= min_diff_ticks * tick_size
    top = max(close_prev, open_curr) · bottom = min(...)
    el gap se ancla en el **boundary**: `Times[1][1]`, o sea el timestamp de la
    barra M1 ANTERIOR — no la actual.

SEÑAL (`overlap_at_birth`)
    Confluencia conocida AL NACER, sin lookahead: cuántas zonas vivas se solapan
    con la nueva en precio y en tiempo. Arranca en 1 (se cuenta a sí misma) y
    suma 1 por cada solape. El `.cs` incrementa también el contador de las zonas
    viejas, pero ese valor futuro NO se exporta — el logger guarda el valor al
    nacer, que es el único usable como feature causal.

VENTANA DE VIDA
    `expires_m1_bar = start_m1_bar + extend_bars`, medida en BARRAS M1. Una zona
    vieja cuenta para el solape si `expires_m1_bar >= start_m1_bar(nueva)`.

FUERA DE ALCANCE (declarado)
    `filtrar_por_percentil` afecta SOLO el dibujo y el heatmap del `.cs`; la
    persistencia incluye todos los gaps. Acá se exporta todo, así que el filtro
    es `offline`. `detectar_expansiones` es una capa visual aparte (ZigZag) que
    no produce zonas: no se porta.
"""
from __future__ import annotations

from ..common import ns_to_ms, tz_of

NAME = "AACloseOpenDiffs"

DEFAULTS = dict(
    min_diff_ticks=1,
    extend_bars=50,          # en BARRAS M1: vida de la zona y ventana de solape
    max_zones=5000,
)

PARAM_SPEC = {
    "min_diff_ticks": {"type": "int", "default": 1, "min": 1, "class": "recompute",
                       "branches": ["gap_floor"]},
    "extend_bars": {"type": "int", "default": 50, "min": 1, "class": "recompute",
                    "branches": ["lifetime", "overlap_window"]},
    # Tope defensivo de memoria del `.cs` (MaxRectangles). No cambia qué se
    # detecta mientras no se alcance; se declara `offline` porque su efecto es
    # de truncamiento, no de semántica.
    "max_zones": {"type": "int", "default": 5000, "min": 1, "class": "offline",
                  "branches": ["lifetime"]},
}

HEADER = ("event_seq,event_type,ts,unix_ms,zone_id,start_ms,end_ms,upper,lower,"
          "diff_ticks,direction,overlap_at_birth,m1_bar")


def meta_line(p, instrument, tick_size):
    # v1.2: la versión del meta identifica la SEMÁNTICA, no el archivo. Este
    # kernel siempre comparó el umbral en enteros de tick —nunca tuvo el defecto
    # de `AACloseOpenDiffs.cs` v1.0— pero se etiquetaba `1.0` y por lo tanto la
    # cuarentena de la Decisión B lo marcaba como contaminado. El dato estaba
    # bien; la etiqueta estaba mal. Detectado por el propio escaneo de cuarentena,
    # que es exactamente para lo que sirve.
    return ("# meta indicator=AACloseOpenDiffs,version=1.2,"
            "subseries=minute_1_always,anchor=boundary_prev_m1_close,"
            "overlap=point_in_time_at_birth,bar_spec_independent=true"
            ",instrument={0},tick_size={1},min_diff_ticks={2},extend_bars={3}"
            .format(instrument, tick_size, p["min_diff_ticks"], p["extend_bars"]))


def _m1_bars(ticks):
    """Barras de 1 minuto desde los ticks canónicos — la subserie que usa el `.cs`.

    Se construye acá adentro a propósito: el kernel NO debe depender de las
    barras del chart primario, igual que el `.cs` ignora `BarsInProgress != 1`.
    """
    from .. import bars as bars_mod
    return bars_mod.build_time_bars(ticks, 1)


def run(ticks, bars=None, params=None, chart_tz="UTC"):
    """`bars` se acepta por compatibilidad con el contrato del REGISTRY pero se
    IGNORA: este kernel arma su propia subserie M1. Ver el docstring del módulo."""
    p = {**DEFAULTS, **(params or {})}
    tz = tz_of(chart_tz)
    tick_size = ticks.tick_size
    m1 = _m1_bars(ticks)

    rows, lines, zones = [], [], []
    seq = 0
    zone_seq = 0
    # zonas vivas para el cálculo de solape: (upper_t, lower_t, expires_m1_bar)
    vivas = []

    min_ticks = int(p["min_diff_ticks"])
    extend = int(p["extend_bars"])
    max_zones = int(p["max_zones"])

    def log(etype, t_ns, z):
        nonlocal seq
        from ..common import ts_str
        lines.append("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12}".format(
            seq, etype, ts_str(t_ns, tz), ns_to_ms(t_ns), z["id"],
            z["start_ms"], z["end_ms"], z["upper"], z["lower"],
            z["diff_ticks"], z["direction"], z["overlap_at_birth"], z["m1_bar"]))
        rows.append(dict(seq=seq, type=etype, ts_ns=int(t_ns), unix_ms=ns_to_ms(t_ns),
                         zone_id=z["id"]))
        seq += 1

    # El `.cs` arranca en CurrentBars[1] >= 1: necesita la barra M1 anterior.
    for b in range(1, len(m1)):
        close_prev = int(m1.close_t[b - 1])
        open_curr = int(m1.open_t[b])
        # Aritmética en ENTEROS de tick (lección permanente del contrato §5):
        # el `.cs` compara `gapPts < MinDiffTicks * TickSize` sobre doubles, pero
        # ambos operandos derivan de precios de grilla y la diferencia es un
        # múltiplo exacto del tick, así que el entero es equivalente y exacto.
        diff_ticks = abs(close_prev - open_curr)
        if diff_ticks < min_ticks:
            continue

        upper_t = max(close_prev, open_curr)
        lower_t = min(close_prev, open_curr)
        # ANCLA: el boundary es la barra M1 ANTERIOR (`Times[1][1]` en el .cs).
        start_ns = int(m1.end_ns[b - 1])
        expires = b + extend

        # Confluencia AL NACER: solo zonas previas todavía vivas que se solapan
        # en precio. Arranca en 1 (se cuenta a sí misma), igual que el `.cs`.
        overlap = 1
        for (u, lo, exp) in vivas:
            if exp < b:
                continue
            if u < lower_t or lo > upper_t:
                continue
            overlap += 1

        zone_seq += 1
        z = dict(
            id="D{0:06d}".format(zone_seq),
            start_ms=ns_to_ms(start_ns),
            end_ms=ns_to_ms(start_ns) + extend * 60_000,
            upper=upper_t * tick_size, lower=lower_t * tick_size,
            upper_tick=upper_t, lower_tick=lower_t,
            diff_ticks=diff_ticks,
            direction=1 if open_curr > close_prev else -1,
            overlap_at_birth=overlap, m1_bar=b)
        zones.append(z)
        vivas.append((upper_t, lower_t, expires))
        # Poda: las ya expiradas no pueden volver a solapar. Mantiene la búsqueda
        # acotada sin cambiar el resultado.
        if len(vivas) > max_zones:
            vivas = [v for v in vivas if v[2] >= b][-max_zones:]
        log("ZONE_CREATED", start_ns, z)

    # `created_bar` EXPORTADO (13.63). Este kernel ya lo tenía —se llama
    # `m1_bar`— pero con OTRO nombre, así que el reloj de disponibilidad de la
    # curva de diseño no lo encontraba y descartaba las 144.511 zonas enteras.
    # La identidad está verificada: `_m1_bars(ticks)` == `build_time_bars(ticks, 1)`
    # (6.703 barras, `end_ns` idéntico), o sea que `m1_bar` indexa exactamente la
    # misma grilla que el `created_bar` de los otros cinco kernels.
    # Se exporta con el nombre canónico y se DEJA `m1_bar` en `features`: hay
    # oráculos y goldens que lo nombran así, y renombrar rompería paridad.
    out = [dict(id=z["id"], indicator=NAME, top=z["upper"], bottom=z["lower"],
                created_ms=z["start_ms"], ended_ms=z["end_ms"], state="EXPIRED",
                created_bar=z["m1_bar"],
                kind="gap_up" if z["direction"] == 1 else "gap_down",
                touches=0, end_reason="extend_bars", timeline=[],
                lower_tick=z["lower_tick"], upper_tick=z["upper_tick"],
                features=dict(diff_ticks=z["diff_ticks"],
                              overlap_at_birth=z["overlap_at_birth"],
                              m1_bar=z["m1_bar"]))
           for z in zones]

    return dict(indicator=NAME, params=p, header=HEADER, csv_lines=lines,
                events=rows, zones=out, n_m1_bars=len(m1),
                params_line=meta_line(p, ticks.instrument, tick_size))
