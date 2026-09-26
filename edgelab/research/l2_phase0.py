"""Fase 0 del plan L2 (docs/research/PLAN_L2_POST_DEEP_RESEARCH_20260923.md): QA, costos y reloj de eventos.

TARGET-FREE en el sentido del proyecto: no mira retornos de ninguna regla ni selecciona nada por P&L. Mide
(a) integridad de la sesion, (b) costo mecanico de operar (spread, profundidad, barrido de N contratos, spread
efectivo de los trades) y (c) cuanto tarda el mid en cambiar k veces. Solo para sesiones PRE-HOLDOUT: los costos
no se calibran con el holdout (NORTH_STAR, firewall).

Convenciones:
- Libro: MBP-10 de NT8, reconstruido con la misma semantica que `tools/build_l2_viewer_bundle.apply_l2`
  (op 0 = alta en la posicion `level`, 1 = cambio, 2 = baja). Un evento invalido se cuenta y se descarta.
- PSEUDO-EVENTOS: las filas con el mismo `ts_us` forman un grupo atomico (un mismo match puede llegar como varias
  filas). El estado del libro solo se LEE al cierre de un grupo; nunca "entre" filas del mismo grupo.
- Bootstrap: no se mide nada hasta que los dos lados tienen 10 niveles y pasaron `BOOTSTRAP_S` segundos desde ahi.
- Tiempo: `ts_us` es reloj de pared ART (UTC-3) leido como UTC; los bloques de 30 min se rotulan en ese reloj.
- Todo en TICKS (enteros del parquet), independiente del tamaño de tick del instrumento.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

ASK, BID = 0, 1
LEVELS = 10
BOOTSTRAP_S = 60
SWEEP_SIZES = (1, 2, 5, 10)
CLOCK_KS = (2, 10, 100)
BLOCK_S = 1800


INVALID, OK, EDGE_RESYNC = 0, 1, 2
TAIL_DELETE = EDGE_RESYNC      # nombre anterior (2026-09-23 temprano); se conserva por compatibilidad


def _ordered_after_last(book: list, side: int, tick: int) -> bool:
    """True si `tick` va DESPUES del ultimo nivel del lado (ask: mas caro; bid: mas barato) o el lado esta vacio."""
    if not book:
        return True
    return tick > book[-1][0] if side == ASK else tick < book[-1][0]


def apply_event(book: list, op: int, lvl: int, tick: int, size: int, side: int | None = None) -> int:
    """Aplica un evento MBP-10 de NT8 a un lado (posicion 0 = mejor precio). Devuelve INVALID, OK o EDGE_RESYNC.

    RESINCRONIZACION DEL BORDE (decision P-75, 2026-09-23, delegada por Nico). Causa raiz medida: la foto inicial
    (bootstrap) de NT8 a veces omite un nivel de un lado, y desde ahi NT8 direcciona un nivel mas que el libro
    reconstruido. Medido en 7 sesiones (GC 08-26/12-26): 0..19 eventos con precio != precio reconstruido en esa
    posicion, sobre millones (<= 8e-6) y SIN cascada -- el borde profundo se renueva y el libro se resincroniza solo.
    Por eso un evento que apunta MAS ALLA de la profundidad reconstruida no aborta:
      - baja en lvl >= n: si su precio es el del ultimo nivel reconstruido se borra ese nivel; si no, no-op;
      - alta/cambio en lvl > n (alta) o lvl >= n (cambio): se agrega AL FINAL solo si respeta el orden de precios.
    Todo lo demas sigue INVALID (fail-closed). Sin `side` no se puede verificar orden: se trata como INVALID."""
    n = len(book)
    if op == 0:
        if lvl <= n:
            book.insert(lvl, [tick, size])
            if len(book) > LEVELS + 1:      # NT8 manda la baja del nivel desplazado; esto solo evita crecer sin fin
                del book[LEVELS + 1:]
            return OK
        if side is not None and _ordered_after_last(book, side, tick):
            book.append([tick, size])
            return EDGE_RESYNC
        return INVALID
    if op == 1:
        if lvl < n:
            book[lvl] = [tick, size]
            return OK
        if side is not None and _ordered_after_last(book, side, tick):
            book.append([tick, size])
            return EDGE_RESYNC
        return INVALID
    if op == 2:
        if lvl < n:
            del book[lvl]
            return OK
        if n and book[-1][0] == tick:
            del book[-1]
        return EDGE_RESYNC
    return INVALID


def sweep_cost_ticks(levels: list, mid2: int, n: int, side: int) -> float:
    """Costo de consumir `n` contratos del lado `side` (ASK = comprar) contra el mid, en ticks. NaN si no alcanza.
    `mid2` es 2*mid en ticks (entero, evita medios ticks en float)."""
    rem, acc = n, 0
    for tick, size in levels[:LEVELS]:
        take = min(rem, size)
        acc += take * tick
        rem -= take
        if rem == 0:
            break
    if rem:
        return float("nan")
    vwap2 = 2 * acc / n
    return (vwap2 - mid2) / 2 if side == ASK else (mid2 - vwap2) / 2


@dataclass
class SessionResult:
    qa: dict
    snaps: dict = field(default_factory=dict)     # arrays por snapshot de 1 s
    trades: dict = field(default_factory=dict)    # arrays por trade
    mid_change_ts: np.ndarray = None              # us de cada cambio de mid (cierre de grupo)


def process_session(l2, l1) -> SessionResult:
    """`l2`: columnas side, operation, level, price_tick, size, ts_us, source_row. `l1`: side, price_tick, size,
    ts_us, source_row (side 2 = trade). DataFrames de pandas o dict de arrays."""
    o2 = np.argsort(np.asarray(l2["source_row"]), kind="stable")
    sd = np.asarray(l2["side"])[o2]; op = np.asarray(l2["operation"])[o2]; lv = np.asarray(l2["level"])[o2]
    tk = np.asarray(l2["price_tick"])[o2]; sz = np.asarray(l2["size"])[o2]; ts = np.asarray(l2["ts_us"])[o2]
    r2 = np.asarray(l2["source_row"])[o2]
    m1 = np.asarray(l1["side"]) == 2
    t_row = np.asarray(l1["source_row"])[m1]; o1 = np.argsort(t_row, kind="stable")
    t_row = t_row[o1]; t_tick = np.asarray(l1["price_tick"])[m1][o1]; t_size = np.asarray(l1["size"])[m1][o1]
    t_ts = np.asarray(l1["ts_us"])[m1][o1]

    asks, bids = [], []
    invalid = inversions = crossed_groups = groups = tail_deletes = 0
    full_since = None
    snap = {k: [] for k in ("t", "bid", "ask", "bid_sz", "ask_sz")}
    for n_ in SWEEP_SIZES:
        snap[f"buy{n_}"] = []; snap[f"sell{n_}"] = []
    tr = {k: [] for k in ("t", "tick", "size", "eff_half_spread", "spread")}
    mid_changes, last_mid2 = [], None
    last_sec = None
    ti, nt = 0, len(t_row)
    prev_ts = None
    N = len(ts)

    def valid_now(t):
        return full_since is not None and t - full_since >= BOOTSTRAP_S * 1_000_000

    for i in range(N):
        t = int(ts[i])
        if prev_ts is not None and t < prev_ts:
            inversions += 1
        prev_ts = t
        # trades anteriores a este evento: se leen con el libro vigente (cierre del grupo previo)
        while ti < nt and t_row[ti] < r2[i]:
            if bids and asks and valid_now(int(t_ts[ti])):
                b, a = bids[0][0], asks[0][0]
                mid2 = a + b
                tr["t"].append(int(t_ts[ti])); tr["tick"].append(int(t_tick[ti])); tr["size"].append(int(t_size[ti]))
                tr["eff_half_spread"].append(abs(2 * int(t_tick[ti]) - mid2) / 2); tr["spread"].append(a - b)
            ti += 1
        rc = apply_event(asks if sd[i] == ASK else bids, int(op[i]), int(lv[i]), int(tk[i]), int(sz[i]), int(sd[i]))
        if rc == INVALID:
            invalid += 1
        elif rc == EDGE_RESYNC:
            tail_deletes += 1
        end_of_group = i == N - 1 or int(ts[i + 1]) != t
        if not end_of_group:
            continue
        groups += 1
        if full_since is None and len(asks) >= LEVELS and len(bids) >= LEVELS:
            full_since = t
        if not (asks and bids):
            continue
        b, a = bids[0][0], asks[0][0]
        if b >= a:
            crossed_groups += 1
            continue
        mid2 = a + b
        if valid_now(t):
            if last_mid2 is not None and mid2 != last_mid2:
                mid_changes.append(t)
            last_mid2 = mid2
            sec = t // 1_000_000
            if sec != last_sec:
                last_sec = sec
                snap["t"].append(t); snap["bid"].append(b); snap["ask"].append(a)
                snap["bid_sz"].append([s for _, s in bids[:LEVELS]] + [0] * (LEVELS - min(LEVELS, len(bids))))
                snap["ask_sz"].append([s for _, s in asks[:LEVELS]] + [0] * (LEVELS - min(LEVELS, len(asks))))
                for n_ in SWEEP_SIZES:
                    snap[f"buy{n_}"].append(sweep_cost_ticks(asks, mid2, n_, ASK))
                    snap[f"sell{n_}"].append(sweep_cost_ticks(bids, mid2, n_, BID))
    qa = dict(l2_events=N, groups=groups, invalid_events=invalid, edge_resync_events=tail_deletes, clock_inversions=inversions,
              crossed_group_ratio=crossed_groups / max(1, groups), trades=nt, trades_measured=len(tr["t"]),
              bootstrap_complete=full_since is not None, snapshots=len(snap["t"]),
              first_ts_us=int(ts[0]) if N else None, last_ts_us=int(ts[-1]) if N else None)
    return SessionResult(qa=qa, snaps={k: np.asarray(v) for k, v in snap.items()},
                         trades={k: np.asarray(v) for k, v in tr.items()},
                         mid_change_ts=np.asarray(mid_changes, dtype=np.int64))


def defect_reasons(qa: dict, *, max_crossed=0.01, max_edge_resync_rate=1e-3) -> list[str]:
    """Motivos (vacio = sesion usable). Regla fija ANTES de mirar nada economico."""
    out = []
    if qa["invalid_events"]:
        out.append(f"INVALID_EVENTS={qa['invalid_events']}")
    # P-75: la resincronizacion del borde se tolera, pero no sin limite. Umbral fijado ANTES de mirar nada economico.
    if qa.get("edge_resync_events", 0) > max_edge_resync_rate * max(1, qa["l2_events"]):
        out.append(f"EDGE_RESYNC_RATE={qa['edge_resync_events'] / max(1, qa['l2_events']):.2e}")
    if qa["clock_inversions"]:
        out.append(f"CLOCK_INVERSIONS={qa['clock_inversions']}")
    if qa["crossed_group_ratio"] > max_crossed:
        out.append(f"CROSSED_RATIO={qa['crossed_group_ratio']:.4f}")
    if not qa["bootstrap_complete"]:
        out.append("BOOK_NEVER_FULL")
    if qa["snapshots"] < 3600:
        out.append(f"FEW_SNAPSHOTS={qa['snapshots']}")
    return out


def time_to_k_changes(sample_t: np.ndarray, change_t: np.ndarray, k: int) -> np.ndarray:
    """Segundos desde cada `sample_t` hasta el k-esimo cambio de mid posterior (NaN si no ocurre en la sesion)."""
    idx = np.searchsorted(change_t, sample_t, side="right") + (k - 1)
    out = np.full(len(sample_t), np.nan)
    ok = idx < len(change_t)
    out[ok] = (change_t[idx[ok]] - sample_t[ok]) / 1e6
    return out


def block_table(res: SessionResult, *, instrument: str, contract: str, session: str):
    """Tabla por bloque de 30 min (reloj de pared ART): costos y reloj de eventos. Devuelve lista de dicts."""
    s = res.snaps
    if len(s.get("t", [])) == 0:
        return []
    blk = (s["t"] // 1_000_000 % 86400) // BLOCK_S
    spread = s["ask"] - s["bid"]
    bsz, asz = np.asarray(s["bid_sz"], dtype=float), np.asarray(s["ask_sz"], dtype=float)
    clocks = {k: time_to_k_changes(s["t"], res.mid_change_ts, k) for k in CLOCK_KS}
    tr = res.trades
    tblk = (tr["t"] // 1_000_000 % 86400) // BLOCK_S if len(tr.get("t", [])) else np.array([])
    rows = []
    for b in np.unique(blk):
        m = blk == b
        row = dict(instrument=instrument, contract=contract, session=session,
                   block_art=f"{int(b) * 30 // 60:02d}:{int(b) * 30 % 60:02d}", seconds=int(m.sum()),
                   spread_mean_ticks=float(spread[m].mean()), spread_1tick_share=float((spread[m] == 1).mean()),
                   depth_l1_bid=float(bsz[m, 0].mean()), depth_l1_ask=float(asz[m, 0].mean()),
                   depth_l10_bid=float(bsz[m].sum(1).mean()), depth_l10_ask=float(asz[m].sum(1).mean()))
        for n_ in SWEEP_SIZES:
            c = np.concatenate([s[f"buy{n_}"][m], s[f"sell{n_}"][m]])
            ok = ~np.isnan(c)
            row[f"sweep{n_}_p50"] = float(np.median(c[ok])) if ok.any() else np.nan
            row[f"sweep{n_}_p90"] = float(np.percentile(c[ok], 90)) if ok.any() else np.nan
            row[f"sweep{n_}_insufficient_share"] = float(1 - ok.mean())
        for k in CLOCK_KS:
            c = clocks[k][m]; ok = ~np.isnan(c)
            row[f"t{k}_changes_p50_s"] = float(np.median(c[ok])) if ok.any() else np.nan
            row[f"t{k}_changes_p10_s"] = float(np.percentile(c[ok], 10)) if ok.any() else np.nan
        mt = tblk == b
        row["trades"] = int(mt.sum())
        row["eff_half_spread_mean"] = float(tr["eff_half_spread"][mt].mean()) if mt.any() else np.nan
        row["eff_half_spread_volw"] = (float((tr["eff_half_spread"][mt] * tr["size"][mt]).sum() / tr["size"][mt].sum())
                                       if mt.any() else np.nan)
        rows.append(row)
    return rows
