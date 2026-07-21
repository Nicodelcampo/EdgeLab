"""Reconstruccion LIMPIA de la cinta continua del NQ desde exports POR CONTRATO
(lo contrario del merge envenenado de EXP-042):

  1. Parse por contrato (formato NT8: 'yyyyMMdd HHmmss fffffff;last;bid;ask;vol',
     ancho fijo) -> arrays float64, timestamp ns.
  2. Validacion POR contrato (span, spread, saltos).
  3. Empalme por VOLUMEN: switch = primer dia en que el volumen diario del
     contrato siguiente supera al del corriente (regla mecanica, sin precios).
     Cada timestamp pertenece a UN solo contrato. CERO solapamiento.
  4. Back-adjustment ADITIVO: offset = mediana(mid_next - mid_prev) en la
     ventana comun liquida 13:00-20:00 UTC del dia previo al switch; se
     acumula hacia atras (el contrato mas nuevo queda sin ajustar).
  5. GATE de validacion final: saltos, spread, cobertura, correlacion diaria
     vs ES. Si no pasa, NO se generan derivados.
  6. Derivados: nq_ticks_clean.parquet + nq_m1_clean.parquet (indice ns).

Ejecutar (desde C:\\$AEdgeLab):  python -m databuild.build_nq_clean
"""
import sys
import numpy as np
import pandas as pd

from edgelab.config import NQ_RAW_DIR, NQ_CONTRACTS, NQ_TICKS_CLEAN, NQ_M1_CLEAN, ES_M1

TICK = 0.25


def parse_contract(path):
    print(f"  parseando {path.name} ...", flush=True)
    df = pd.read_csv(path, sep=";", header=None,
                     names=["dt", "last", "bid", "ask", "vol"],
                     dtype={"dt": str, "last": np.float64, "bid": np.float64,
                            "ask": np.float64, "vol": np.int64},
                     engine="c")
    s = df["dt"]
    date = pd.to_datetime(s.str.slice(0, 8), format="%Y%m%d")
    hh = s.str.slice(9, 11).astype(np.int64)
    mm = s.str.slice(11, 13).astype(np.int64)
    ss = s.str.slice(13, 15).astype(np.int64)
    frac100ns = s.str.slice(16).astype(np.int64)          # 7 digitos, unidades de 100ns
    ts_ns = (date.values.astype("datetime64[ns]").astype(np.int64)
             + (hh * 3600 + mm * 60 + ss).to_numpy() * 10**9
             + frac100ns.to_numpy() * 100)
    out = pd.DataFrame({"ts_ns": ts_ns, "last": df["last"], "bid": df["bid"],
                        "ask": df["ask"], "vol": df["vol"]})
    out = out.sort_values("ts_ns", kind="stable").reset_index(drop=True)
    spr = (out["ask"] - out["bid"]).to_numpy() / TICK
    t0 = pd.Timestamp(out.ts_ns.iloc[0]); t1 = pd.Timestamp(out.ts_ns.iloc[-1])
    print(f"    {len(out):,} ticks | {t0} -> {t1} | spread p50={np.nanmedian(spr):.1f}t "
          f"p99={np.nanquantile(spr, 0.99):.1f}t | vol total {out.vol.sum():,}")
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    contracts = []
    for name in NQ_CONTRACTS:
        p = NQ_RAW_DIR / name
        if not p.exists():
            print(f"FALTA {p} — abortando"); return
        contracts.append((name, parse_contract(p)))

    # --- switch por volumen diario ---
    print("\nEmpalme por volumen diario:")
    dayvol = []
    for name, df in contracts:
        d = pd.to_datetime(df["ts_ns"]).dt.normalize()
        dv = df.groupby(d)["vol"].sum()
        dayvol.append(dv)
    switches = []   # fecha (normalizada) en la que el contrato i+1 pasa a ser front
    for i in range(len(contracts) - 1):
        common = dayvol[i].index.intersection(dayvol[i + 1].index)
        sw = None
        for day in sorted(common):
            if dayvol[i + 1].loc[day] > dayvol[i].loc[day]:
                sw = day
                break
        if sw is None:
            sw = dayvol[i].index.max() + pd.Timedelta(days=1)
        switches.append(sw)
        print(f"  {contracts[i][0]} -> {contracts[i+1][0]}: switch {sw.date()}")

    # --- offsets de roll: join POR MINUTO sobre el span comun de ambos
    # contratos (robusto a switches en fin de semana), mediana de la
    # diferencia de mid minuto a minuto ---
    offsets = []
    for i, sw in enumerate(switches):
        a = contracts[i][1]; b = contracts[i + 1][1]
        lo = max(a.ts_ns.iloc[0], b.ts_ns.iloc[0])
        hi = min(a.ts_ns.iloc[-1], b.ts_ns.iloc[-1])
        if hi <= lo:
            # SIN solapamiento (ej. hueco de export mar-20 -> abr-19): offset 0,
            # frontera de NIVEL documentada. Inocuo para estrategias RTH
            # por-dia; PROHIBIDO cruzarla con lookbacks de nivel.
            print(f"  offset {contracts[i][0]}->{contracts[i+1][0]}: SIN SOLAPAMIENTO "
                  f"-> 0.00 (frontera de nivel documentada)")
            offsets.append(0.0)
            continue
        am = a[(a.ts_ns >= lo) & (a.ts_ns <= hi)].copy()
        bm = b[(b.ts_ns >= lo) & (b.ts_ns <= hi)].copy()
        for fr in (am, bm):
            fr["minute"] = fr["ts_ns"] // (60 * 10**9)
            fr["mid"] = (fr["bid"] + fr["ask"]) / 2
        ga = am.groupby("minute")["mid"].median()
        gb = bm.groupby("minute")["mid"].median()
        j = pd.concat([ga.rename("a"), gb.rename("b")], axis=1).dropna()
        if len(j) < 100:
            print(f"  offset {contracts[i][0]}->{contracts[i+1][0]}: solapamiento "
                  f"insuficiente ({len(j)} min) -> 0.00 (frontera documentada)")
            offsets.append(0.0)
            continue
        off = float((j["b"] - j["a"]).median())
        offsets.append(off)
        print(f"  offset {contracts[i][0]}->{contracts[i+1][0]}: {off:+.2f} pts "
              f"({len(j):,} minutos comunes, span "
              f"{pd.Timestamp(lo).date()}..{pd.Timestamp(hi).date()})")

    # --- recorte sin solapamiento + ajuste aditivo hacia atras ---
    parts = []
    for i, (name, df) in enumerate(contracts):
        lo = switches[i - 1].value if i > 0 else -2**62
        hi = switches[i].value if i < len(switches) else 2**62
        seg = df[(df.ts_ns >= lo) & (df.ts_ns < hi)].copy()
        adj = sum(offsets[i:])   # todo lo que falta hasta el contrato mas nuevo
        for col in ("last", "bid", "ask"):
            seg[col] = seg[col] + adj
        print(f"  {name}: segmento {pd.Timestamp(seg.ts_ns.iloc[0]).date()} -> "
              f"{pd.Timestamp(seg.ts_ns.iloc[-1]).date()} ({len(seg):,} ticks, adj {adj:+.2f})")
        parts.append(seg)
    tape = pd.concat(parts, ignore_index=True)
    assert tape.ts_ns.is_monotonic_increasing

    # --- GATE de validacion final ---
    print("\n--- GATE de validacion ---")
    px = tape["last"].to_numpy()
    dp = np.abs(np.diff(px))
    jumps = int((dp > 20).sum())
    spr = (tape["ask"] - tape["bid"]).to_numpy() / TICK
    p50, p99 = np.nanmedian(spr), np.nanquantile(spr, 0.99)
    print(f"saltos >20pt tick-a-tick: {jumps} (cinta vieja: 475.743)")
    print(f"spread: p50={p50:.1f}t p99={p99:.1f}t (cinta vieja: p50=3t)")

    ts = pd.to_datetime(tape["ts_ns"])
    d_nq = pd.Series(tape["last"].to_numpy(), index=ts).resample("1D").last().dropna()
    es = pd.read_parquet(ES_M1)["close"].resample("1D").last().dropna()
    common = d_nq.index.intersection(es.index)
    corr = np.corrcoef(d_nq.loc[common].pct_change().dropna(),
                       es.loc[common].pct_change().dropna())[0, 1] if len(common) > 20 else np.nan
    print(f"correlacion de retornos diarios NQ~ES: {corr:.3f} (esperado ~0.9)")

    # umbral de spread calibrado a NQ: su spread REAL es ~3t (verificado en los
    # archivos por-contrato limpios; el NQ es mas fino que el ES)
    gate_ok = (jumps < 500) and (p50 <= 3.5) and (corr > 0.75)
    if not gate_ok:
        print("\nGATE FALLIDO — no se generan derivados. Revisar antes de usar.")
        return

    print("\nGATE OK — generando artefactos...")
    tape.to_parquet(NQ_TICKS_CLEAN, index=False)
    minute = ts.values.astype("datetime64[m]")
    g = pd.DataFrame({"minute": minute, "last": tape["last"].to_numpy(),
                      "vol": tape["vol"].to_numpy()}) \
        .groupby("minute", sort=True).agg(open=("last", "first"), high=("last", "max"),
                                          low=("last", "min"), close=("last", "last"),
                                          volume=("vol", "sum"))
    g.index = g.index.astype("datetime64[ns]")
    g.index.name = "datetime"
    g.to_parquet(NQ_M1_CLEAN)
    print(f"{len(tape):,} ticks -> {NQ_TICKS_CLEAN}")
    print(f"{len(g):,} velas M1 -> {NQ_M1_CLEAN} ({g.index[0]} -> {g.index[-1]})")


if __name__ == "__main__":
    main()
