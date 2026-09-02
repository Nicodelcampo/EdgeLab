"""Parser de los CSV/logs de eventos que exportan los indicadores NT8
(EventLogPath). Normaliza los eventos a zonas comparables con las del kernel
Python (paridad P2A/P2B).

Formatos soportados:
- CSV con coma + líneas '# meta'/'# params': Gaps2, HFTZones2, VolTicksPOC2,
  aVolCellPOI2.
- Formato pipe 'seq|iso|type|payload': BigTrap2.

Los timestamps 'ts'/'bar_close_time' de NT8 vienen en hora del gráfico, por eso
el parser exige `chart_tz` cuando el CSV no trae unix_ms. NUNCA se fabrica un
CSV NT8 ficticio para declarar paridad: este parser consume exports reales.
"""
from __future__ import annotations

from datetime import datetime

from .common import tz_of

from . import quarantine


def _to_unix_ms(s, tz):
    s = (s or "").strip()
    if not s:
        return None
    base, frac = s, "0"
    if "." in s:
        base, frac = s.split(".", 1)
    fmt = "%Y-%m-%dT%H:%M:%S" if "T" in base else "%Y-%m-%d %H:%M:%S"
    d = datetime.strptime(base, fmt).replace(tzinfo=tz)
    ms = int(round(float("0." + frac) * 1000)) if frac else 0
    return int(d.timestamp()) * 1000 + ms


def _f(s):
    s = (s or "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_payload(payload):
    out = {}
    for part in payload.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def parse_records(lines, chart_tz="UTC", tick_size=None):
    """Igual que parse_nt8_log pero desde líneas en memoria (mismo formato que
    exporta el kernel Python: params_line + header + csv_lines). Usado por el
    store para reconstruir zonas desde el propio EventLog del kernel."""
    tz = tz_of(chart_tz)
    raw = [ln.rstrip("\r\n") for ln in lines if ln and ln.strip()]
    meta_lines = [ln for ln in raw if ln.startswith("#")]
    body = [ln for ln in raw if not ln.startswith("#")]
    meta = " ".join(meta_lines)
    if body and body[0].count("|") >= 3 and "," not in body[0].split("|", 2)[0]:
        return _parse_pipe(body, meta, tz)
    if "indicator=BigTrap2" in meta:
        return _parse_pipe(body, meta, tz)
    return _parse_csv(body, meta, tz, tick_size)


def parse_nt8_log(path, chart_tz="UTC", tick_size=None, *, allow_quarantined=False):
    """Devuelve dict(indicator, meta, header, events, zones).

    **Filtro de cuarentena estructural (Decisión B de Nico, 2026-07-26).** Antes
    de parsear nada se consulta `quarantine`: un archivo generado por una versión
    en cuarentena levanta `DatosEnCuarentena`. No hay que acordarse de excluirlo —
    hay que desactivarlo a propósito con `allow_quarantined=True`, y eso deja
    rastro en el código que lo hace.

    El escape existe sólo para el forense: leer los datos sucios para MEDIR el
    defecto es legítimo; usarlos como insumo no.
    """
    with open(path, "r", encoding="utf-8-sig") as fh:
        lines = [ln.rstrip("\r\n") for ln in fh if ln.strip()]
    if not allow_quarantined:
        quarantine.verificar(" ".join(l for l in lines if l.startswith("#")), path)
    return parse_records(lines, chart_tz=chart_tz, tick_size=tick_size)


def _detect_indicator(meta, header):
    for name in ("Gaps2", "HFTZones2", "VolTicksPOC2", "aVolClusterPOI", "aVolCellPOI2", "BigTrap2",
                 "AACloseOpenDiffs"):
        if "indicator=" + name in meta:
            return name
    if "gap_id" in header:
        return "Gaps2"
    if "calib_id" in header:
        return "HFTZones2"
    if "poc_tick" in header:
        return "VolTicksPOC2"
    if "selected_lower_tick" in header or ("cluster" in meta.lower()):
        return "aVolClusterPOI"
    if "bucket" in header and "lower_tick" in header:
        return "aVolCellPOI2"
    if "overlap_at_birth" in header:
        return "AACloseOpenDiffs"
    return "unknown"


_END_STATES = {"ZONE_INVALIDATED": "INVALIDATED", "ZONE_EXPIRED": "EXPIRED"}


def _parse_csv(body, meta, tz, tick_size):
    header = body[0].split(",")
    idx = {name: i for i, name in enumerate(header)}
    indicator = _detect_indicator(meta, header)
    events, zones = [], {}

    def col(parts, name):
        i = idx.get(name)
        return parts[i] if i is not None and i < len(parts) else ""

    for ln in body[1:]:
        parts = ln.split(",")
        events.append(dict(zip(header, parts)))
        etype = col(parts, "event_type")
        if indicator == "AACloseOpenDiffs":
            # Una linea por zona, emitida AL NACER. No hay eventos de ciclo de
            # vida: la zona vive `extend_bars` barras M1 y expira sola, asi que
            # `ended_ms` viene ya calculado en la propia fila (`end_ms`).
            zid = col(parts, "zone_id")
            if not zid:
                continue
            zones[zid] = dict(
                id=zid, indicator=indicator,
                top=_f(col(parts, "upper")), bottom=_f(col(parts, "lower")),
                created_ms=_f(col(parts, "start_ms")),
                ended_ms=_f(col(parts, "end_ms")),
                state="EXPIRED",
                kind="gap_up" if _f(col(parts, "direction")) == 1 else "gap_down",
                touches=0, end_reason="extend_bars",
                diff_ticks=_f(col(parts, "diff_ticks")),
                overlap_at_birth=_f(col(parts, "overlap_at_birth")))
            continue
        if indicator == "Gaps2":
            zid = col(parts, "gap_id")
            if not zid:
                continue
            unix_ms = _f(col(parts, "unix_ms"))
            z = zones.setdefault(zid, dict(
                id=zid, indicator=indicator,
                top=_f(col(parts, "top")), bottom=_f(col(parts, "bottom")),
                created_ms=_f(col(parts, "created_unix_ms")), ended_ms=None,
                state=None, kind="gap", touches=0, end_reason=None))
            st = col(parts, "state")
            if st:
                z["state"] = st.upper()
            t = _f(col(parts, "touches"))
            if t is not None:
                z["touches"] = int(t)
            if etype in ("ZONE_INVALIDATED", "ZONE_EXPIRED"):
                z["ended_ms"] = unix_ms
                z["end_reason"] = col(parts, "extra") or etype.lower()
        elif indicator == "HFTZones2":
            zid = col(parts, "zone_id")
            if not zid:
                continue
            unix_ms = _f(col(parts, "unix_ms"))
            z = zones.setdefault(zid, dict(
                id=zid, indicator=indicator,
                top=_f(col(parts, "upper")), bottom=_f(col(parts, "lower")),
                created_ms=unix_ms if etype in ("ZONE_CREATED", "OBS") else None,
                ended_ms=None, state="ACTIVE",
                kind=(col(parts, "bucket") or "zone").lower(),
                touches=0, end_reason=None))
            if z["created_ms"] is None and etype == "ZONE_CREATED":
                z["created_ms"] = unix_ms
            t = _f(col(parts, "touches"))
            if t is not None:
                z["touches"] = int(t)
            if etype in _END_STATES:
                z["state"] = _END_STATES[etype]
                z["ended_ms"] = unix_ms
                z["end_reason"] = col(parts, "reason") or None
        elif indicator == "VolTicksPOC2":
            zid = col(parts, "zone_id")
            if not zid or zid == "0":
                continue
            unix_ms = _to_unix_ms(col(parts, "bar_close_time"), tz)
            poc = _f(col(parts, "poc_tick"))
            top = (poc + 0.5) * tick_size if (poc is not None and tick_size) else poc
            bottom = (poc - 0.5) * tick_size if (poc is not None and tick_size) else poc
            z = zones.setdefault(zid, dict(
                id=zid, indicator=indicator, top=top, bottom=bottom,
                created_ms=unix_ms if etype == "ZONE_CREATED" else None,
                ended_ms=None, state="ACTIVE", kind="poc_anomaly",
                touches=0, end_reason=None))
            if z["created_ms"] is None and etype == "ZONE_CREATED":
                z["created_ms"] = unix_ms
            t = _f(col(parts, "touch_count"))
            if t is not None:
                z["touches"] = int(t)
            if etype in _END_STATES:
                z["state"] = _END_STATES[etype]
                z["ended_ms"] = unix_ms
                z["end_reason"] = col(parts, "reason") or None
        elif indicator == "aVolClusterPOI":
            zid = col(parts, "zone_id")
            if not zid or zid == "0":
                continue
            unix_ms = _to_unix_ms(col(parts, "bar_close_time"), tz)
            lo_t, hi_t = _f(col(parts, "lower_tick")), _f(col(parts, "upper_tick"))
            top = (hi_t + 0.5) * tick_size if (hi_t is not None and tick_size) else hi_t
            bottom = (lo_t - 0.5) * tick_size if (lo_t is not None and tick_size) else lo_t
            if etype == "ZONE_CREATED":
                z = zones.setdefault(zid, dict(
                    id=zid, indicator=indicator, top=top, bottom=bottom,
                    created_ms=unix_ms, ended_ms=None, state="ACTIVE",
                    kind="avol_cluster_off_price", touches=0, end_reason=None))
            elif etype in _END_STATES and zid in zones:
                z = zones[zid]
                z["state"] = _END_STATES[etype]
                z["ended_ms"] = unix_ms
                z["end_reason"] = col(parts, "reason") or None
            elif etype == "ZONE_TOUCHED" and zid in zones:
                t = _f(col(parts, "touch_count"))
                if t is not None:
                    zones[zid]["touches"] = int(t)
        elif indicator == "aVolCellPOI2":
            zid = col(parts, "zone_id")
            if not zid or zid == "0":
                continue
            unix_ms = _to_unix_ms(col(parts, "bar_close_time"), tz)
            lo_t, hi_t = _f(col(parts, "lower_tick")), _f(col(parts, "upper_tick"))
            top = (hi_t + 0.5) * tick_size if (hi_t is not None and tick_size) else hi_t
            bottom = (lo_t - 0.5) * tick_size if (lo_t is not None and tick_size) else lo_t
            z = zones.setdefault(zid, dict(
                id=zid, indicator=indicator, top=top, bottom=bottom,
                created_ms=unix_ms if etype == "ZONE_CREATED" else None,
                ended_ms=None, state="ACTIVE", kind="vol_cell_poi",
                touches=0, end_reason=None))
            if z["created_ms"] is None and etype == "ZONE_CREATED":
                z["created_ms"] = unix_ms
            t = _f(col(parts, "touch_count"))
            if t is not None:
                z["touches"] = int(t)
            if etype in _END_STATES:
                z["state"] = _END_STATES[etype]
                z["ended_ms"] = unix_ms
                z["end_reason"] = col(parts, "reason") or None
    return dict(indicator=indicator, meta=meta, header=header, events=events,
                session_starts_ns=_session_starts_ns(events, indicator, tz),
                zones=[z for z in zones.values() if z.get("created_ms") is not None
                       or z.get("top") is not None])


# Eventos con los que cada .cs declara que ABRE una sesión. Es la única evidencia
# directa del calendario de NT8 que sale del export; sin ella la alineación de
# calendario no se puede verificar y el preflight lo dice en vez de asumirla.
_INICIO_DE_SESION = {"CALIBRATION", "CALIBRATION_PENDING", "SESSION_START"}


def _ns_de_evento(e, tz):
    """ns UTC de un evento, por `unix_ms` si está y si no por `bar_close_time`.

    `aVolCellPOI2` no exporta `unix_ms`: sólo `bar_close_time` en la timezone del
    chart. Sin este fallback su calendario quedaría SIN VERIFICAR y haría falta
    otra versión del `.cs` sólo para agregar una columna — un export de NT8 de más
    por un dato que ya está ahí.
    """
    ms = _f(e.get("unix_ms"))
    if ms is not None:
        return int(ms) * 1_000_000
    t = e.get("bar_close_time") or e.get("ts")
    if not t:
        return None
    ms = _to_unix_ms(t, tz)
    return int(ms) * 1_000_000 if ms is not None else None


def _session_starts_ns(events, indicator, tz):
    """ts (ns) de los inicios de sesión que declara NT8, si el export los trae.

    HFTZones2 los emite explícitamente (congela la calibración al abrir). Los
    kernels que sólo exportan un `session_index` se resuelven por el cambio de
    ese índice: el primer evento de cada sesión acota la frontera aunque no la
    marque exactamente, que es todo lo que el preflight necesita — `preflight`
    lleva cada instante a la frontera que lo contiene antes de comparar.
    """
    out = []
    for e in events:
        if e.get("event_type") in _INICIO_DE_SESION:
            ns = _ns_de_evento(e, tz)
            if ns is not None:
                out.append(ns)
    if out:
        return sorted(set(out))

    visto = set()
    for e in events:
        si = e.get("session_index")
        if si in (None, "") or si in visto:
            continue
        visto.add(si)
        ns = _ns_de_evento(e, tz)
        if ns is not None:
            out.append(ns)
    return sorted(set(out))


def _parse_pipe(body, meta, tz):
    events, zones = [], {}
    for ln in body:
        parts = ln.split("|", 3)
        if len(parts) < 4:
            continue
        seq, iso, etype, payload = parts
        kv = _parse_payload(payload)
        unix_ms = _to_unix_ms(iso, tz)
        events.append(dict(seq=seq, ts=iso, unix_ms=unix_ms, type=etype, **kv))
        zid = kv.get("zone_id")
        if not zid:
            continue
        z = zones.setdefault(zid, dict(
            id=zid, indicator="BigTrap2",
            top=_f(kv.get("hi")), bottom=_f(kv.get("lo")),
            created_ms=unix_ms if etype == "ZONE_CREATED" else None,
            ended_ms=None, state="ACTIVE",
            kind=kv.get("side", "trap"), touches=0, end_reason=None))
        if z["created_ms"] is None and etype == "ZONE_CREATED":
            z["created_ms"] = unix_ms
        if "touches" in kv:
            try:
                z["touches"] = int(kv["touches"])
            except ValueError:
                pass
        if etype in _END_STATES:
            z["state"] = _END_STATES[etype]
            z["ended_ms"] = unix_ms
            z["end_reason"] = kv.get("reason") or etype.lower()
    return dict(indicator="BigTrap2", meta=meta, header=None, events=events,
                zones=list(zones.values()))
