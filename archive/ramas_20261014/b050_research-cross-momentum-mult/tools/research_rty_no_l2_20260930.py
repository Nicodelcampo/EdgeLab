"""Frozen RTY price-only screen. Private research, not a live strategy."""
from __future__ import annotations
import argparse, base64, hashlib, json, math, platform, sys, time, zlib
from pathlib import Path, PureWindowsPath
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from statistics import NormalDist
class norm:
    ppf = staticmethod(NormalDist().inv_cdf)

NS = 10**9
SEED = 20260930
BOOT = 20000
DISC_END = "20251231"
END = "20260331"
HOLDOUT = 1782856800000000000
CELLS = [(f, tf) for f in ("MOM60", "VWAP2", "ORFAIL30") for tf in (5, 15)]
COMMISSION = 0.9  # USD4.50 roundtrip / USD5 tick; assumption, not actual tariff.
SLIP_SIDE = 1.0
CATALOG = json.loads(zlib.decompress(base64.b64decode("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")))
EXPECTED = json.loads(zlib.decompress(base64.b64decode("eJyVmtuOXcdxhl/F4HVkVZ+7ckeIDEAgomxZDuArog/VgZJIikMGCBDk3fPVkLA4s9YwiqQhqZnN/a+urvoP3fu/X7z886s3P7z79uXbN//w+k8//P5f3v/y84u//92Luk5MYeiwkUSt9qmnDrHRzyplWtwt6sq7rRWznDrjzt109dpj7+e8+Lvfvfj29Z++5uudpK9ifffT+PnHY+8/vLP/+vArjOkMrS4pqn3HVtJqffU1rZ3es4LY+2hSluQ5Dv972tlt9JLCGqteYd7b+/c//vLz+0cwUiMPF0dtpQ2VUlIfM1fj2yXNkrXmPUYZbcXWjwIYa2gm7axZ5ylXmA8/rn/9iPHv4z/++p/2wWHGCS1U1dS2Wt48Ya2zhVj6CSmCvFduvSiFtTGj2RnxjJplrFhXfVy0+mzRFvsy96797D7jshJ7iinHbaLDHz7vKLMfdi7y8Dn0UmuVJKHWWOQG5rZoJwY1G6WOLM2slR3LWFaDjWoxHosl26KSMYcsOZUxzjxt88qy+thXmNui6YkSYztWR99Z2Pkh1dgSlnYq/TByDnWkIlTOBq/c60jYmVZMebRHMPpVLPdFS6PRTxqPhrajNgklRgmx0sJZZVhN+4yiJ8fQUz52VpjhyDm9pRj1CnNbNLqozXhiZreL7CS5ls4k9V0szJlaYeetTso1U67gJmp8Wk+taks3q7kt2qJr1WjbUJI2miEWO0fm2k3XmZmCrrBC1pgWi+XXnmePsZZdVroW7ZlOy1HZBBZx8u5pa6107py19XrqKWVs01SOpFPolqaFzqdBzrGWl1a7wtwWTbXpiKuGWU1OWbTskJWOPDRS0DK0nzLSkkSPNaaqrNmY1AA7sGVXmNuiNUZAx4YKgjIWSUPPq5aYDDKjNyTSZMlAYQ0SWi78GLZrkz3cKX4OE+KznRbz8feCR1LMDHk+jf7J4XRGQwbNHGvvMTA9uQ9RxrVBEv6tGsKpV5jbos3dqYPlZXMPaqInnZ5zmhr3aWXMLjBApSsqs1TZjwX9aYnnpCmmV5jbop0VRysSoag24eFDI58wRXjDs/1tE/QSV06bzt59j7VlhFNaZqDtUrRnOi2tHfdQuNcUYuk1maRmscaWckckxHYGttdcNcxCa5i/rqusAStdYW6L1jXTrHPUFeq0XMMeu3VmXyDo3U5Oa5Q9x5IZGFsdS3VHFtmMnl43q7ktWqoUJdCjhfcErcyH4Qu2NvyCzuQExcgoovV0qXu79jCqSRqNmR5g3v7xa76+pJ7atTNwmxZYoTe0Zuypm3FCpzcEwOS2kEOkkqjOpuVzHPCGphTyJ7J5BHNbtFp4QGh+0rtYga0lz1gSTJAQbWUIG7tyFKJbbIeKtaSnMcuNSqZwhbktWpgJUgkUzKmr62bv4Z95+gwaXef6bKLoQUS8taPbdac6doJW8QaPYJ5XT6YRxRwlo5L7nLCQUfiEvR7BzN9sxITHEPhbuqvSTFbmDgGFbcOuMPfqybOzvWmOAashyDZLRE8AkgKXNm1NNuwSdmPPnFxnoTXzQFp7bFeYe05zNVxtls3b1h3SgfN3nnTrWRswdGyfleyBR89Bm0JYq9KTe0KFj2CeV086k7fRPbuNTGslpKzMqh2CHGX2VBo0kXFzOy8slYWT4jBcg8S1U7nC3BYt00oi2oM65zQ4uVf1vZLeBbPD2MOZ4C3DAOSJG1wpIn8aMqyTrjD36ol0IDM2bY0Yknj/is6I45M9py7Ic4lIo89KwMlt9DooD8EQWL+s5plOiz3jOFfH5+GfkEtLA58k2T3V6HWuWptasCARkaF6Xtqoo1ictdcrzG3RFusPW+YMi5XQUgYuXIlQdxQaETCktOZcUjZMFES0j0RsWnfffq4wt0XDmUnxCrloMkEV5rIkqWCe4MmAv40jCrlBZDKmmx+i63XuxWB/MlCfYL6gnryRrWZzoO+51wbppoBYRmJBUy3MUkmxI0WnMP3wWgvbOqSBwYOurzD3loM+kwprVLE8GH4K1nOrcTCPKH9UvCLycrYVBHyfORE1/h3YIbrhCnNbNIx5SdAH6QXqiCulgZ8oqWL28lyya9I5mKIChWfBdsDTbuFxvhi78xTmmU4LCc8ERTMVzTDlmMyScUrZ8EtYNqJSXJAe1ufBPklPrJRRygPrUG5gbotWJs6uppqZ6oPxxETRRwozBtQl1Dzr8tyDkeU7WPXJi0VS3VIx1HKFuS0aZJxXg/MJfxG9oTyBEAWVtoKTwSdgR88sOKrD7q2Nn5t0hqIXaMPH8fzLt1/z9SX1JNYYlrXQXZbc6mOo4E8cslsEKNXhzNRFCBkKo2fDGowNAaFu5wpzW7RGMNoJOdsFlioJ3lmeqBqGj80K5DgkB8VE9xNTtQuBBLvBX1MMRLzC3BYNjSeWZdcsediM6qH9DMqEaZ+BvsoMvBDTh/EUW5QEdyhyUGJ2eATzvHpCTbaRkIp3IbOkLLAO+9BthdaoP0ED+cTt2lroRQ1KuD9kuBQwUOMKc99pgTnvhxRFkFzu8Hy38QGGoYCEjzsMDYi1Mk3BEz2JIUDpyJ7leIW592mqeRJeIXq0t6pImH5AgLBBZ4xRJQYgbNFcdKiXZCPGrcym5abyCOZ59axFFRnobPrElJ99rLt7JcNFzHNDlseMeKwFj2+d5u4wu40LlPkTdT6CeUYIasNqPhw+MHiT0dyjst37pCQLRsG7o/0ezbTQCIp7IuFaCGPVT8HjEcxt0Saxm8df0/VQN8Ycmqe7CBi99HwqeR5B9v5WQi2ZRBbGpBoGqmOKn8I8lwj6aom9sCk5tARdRxqrIp6SI9mZboPi4D14bW7i4aHKbKdPquyYrjC3RcM+OGPttOZRZiHgyuZqUKPPyZquzkQMHQho7TJgdAS8HfJ6Fzb1CnNbtFxjOdTn0D/4ADYEGZGILMP5bMnAX9IU/Pz4DsLTEtitAqVrkt0+h/mCehaKw9SVtXV3txqMIqI4MARzHegA8ZwYAAyUH+9M9TO20XvzMLq0X2Hui9a3m9rkHn/iXDH9uDxTJh6ubGxTXTAbrKpQt6GnOJGAP8g4qxHPFea2aGhzBAKPXlzDJg5MKCI0eghlI8F0a2fBXYFKh3VydWV/cFANbQ1PYZ7ptIkZJxF6//o8xDVxnRlHSTrY9G7lp1Er9gnfdDDaMYSEwRXakPRerjD35tbzg4UYLVlA3TsZrbID2JfUZIlmbKH0AJFTKfxbogNyi4IF6fD6FebepyHypPDYPRTQs/msGuuBHgvmsDdGEKt7qGPMtDGCZwtRwoogQFgoh/n+9ctX377+/U/7QSeVLcDfrxWIDht2XWuxLR1mNPY+ZSWqKyibQoYSMDDMIbrMIkPJD2/4w1++5utLcnw28Ri/DH8UKJagEXl0Zhw73mmbXEcuHpQZkIL3hJWzS2XqrWFJ1hXmXo4Fe8TKgzuipJVHNYOldjaSZSt0J7nQFdNTZSqOO6Iy7+hY+thTj2HulaUze6Ms9MTP3JCysWPMmOa28zZsZ8mIPcZNd+MFrI+VjQ43iG/eI5jn5TjNFfsogURjDafksql+mC5MS+ju07pbXNKYL63uidupfrKJtISPjuwxzL0cQ8QTXSJPIlK8SRguzIl50UMEIEJ5RiO8+n0AZKJ+DkX0tJWxcPMKc1+0FvD0LYWZj+dw2FbawsYuWTFCxgT1IBWzu+MYKXSccgoDj+1W5rRHMM/LsZ+VDyODZ2zLGWgU/1B8zKwPZCZ2GFIdetGF32P/FfqRk6s7mL6uMLdFixhJAMh1tGzGBlW/I8Fv4i39ZqUWBKflkHAZWEByn5bm5z85VU1mV5h7ZcEKM+ZGJI7EY0qxQyZyFKGN0GkkZvPjwrjWRfCAg1sI7qXTWDDcU5jn3HJZ9LDGzYL4i65RQ6B7ntV8/jucRhTrvDMqXzIBR2i/DjpztvUKc99pyDwplnAniVZAPmw7G6KI61ShaDSW+NF9Jv3FIA3THAzhbkFCrleY+5uaKDSQUwtvg0DNSEr2tG7EZBYHx8+RNrsESy/05sA9BCfMrvl1x+cwX5BjzMJiII0sDoOjGdOOH5wTwmRBL25YDx6/KuxHF48F78066jmpx486+Rjm/nprMv1l4vAwdpZyWuhXaxr5jjG4ATeIk9RE5506OjVDKz15okdV5hXmfjxhXiim0ZuIFFkYpSx7dvFVGoZ8YjACcs0A0QJCTyYnOBMhnu36FOaZTkOAbQg+jl2ebDJGC09GgEQKg9VaiOUoJqsJi44OoVOrRYxtEWeqdoW5LRp5rvJsCEFDRpA1k7Sa32MZCrQw6cQPrRCz3+a0SIzH0qCYg2hLKrjC3J9qMocVoupK4gstJz8gR+lym5jUje7ACVqOnwjPJahDXikaD0R2Dx9PNRH9/yPKNp0VeUcTZS4rgkHBdcXWqss8b488I50D7eH5o8dDtKf7HUsgOD8FuVfOLnh9WatMVhOxczW202Nl9mkE93zkpxzzjoQoOg35jHNBnCHPrheQe/cCpwiGnjhMgRR+ioHdPciwkj397EmV9OXjH8QqgzxzfLhw6KzQPgP5Qogd7PnYFYcqwqj5sXiu8Dtxj9pYnbQYu4BQQ0KbcfEyNdbSIL82noLclyuQ5uOeMRMaN8ruh/00QMt+y7GzH6ZkbZPM3oKR2NYk52BNfDhTWk9B7rNYWq7H7DSWPjQnLKyEwizuoyAy43c0q5Es/arLT88XOsfsb1KTfAbyvF6K+AHbko4RpbEmjnQy2LR1iYiOZwok5+DKtPVJi/Q8MZOYw0UjangKcn9xugbOjC2AC8W1aVKVefbYQxJu1f3p8Gh8MJZUDo1O5vfSZLeIG3gKcn9IoohVYVc8iLYVi58iroCxpGzVT/fxRRAcDmT6zWcoZWZXTvUj7Tkfgzx3GDdH8EdvHeHz876UESz0vqeF4hqi2JlCwrofLmqJfrJMMlt+OG99PQW5LReBehiWfvvV/6rEkp78LmO0HlPcfvfXasLyYTWhSRjyZP+gA0wqcFx4CnLfXcUg771x+2qdqQ99uRGO7jf8sJLhj0Y6gIqhMYad70A0cRrpwMqvIF+6LvXrcboktd0YtiCJ1mRcIOc+0TSMnQT3MiQzDFUi7R1MYYT1JwNcn4Lc2wp8CFPQiMIr+81LjsW9EmRMgDAXZmFRAZrhz3tALLgNbBkCgY8+T0Huu4u4+KDdYmQsvGt3U+LvW0/NnifwNkNgmb2PWWOKJgNFuCCfnWiPQZ4Lq1hSwu/GFa0kOBfJYU0IEAKDAUga5XiMTSUPrAQSxkvYGk+w2MPwFOS2XET7rP7RkdWOLweDgqDk4s1b5yyp079FaK7jx7R7By1TlYb2M5+Tn4Lc3ywLsrA3GuGBtS+LuEtcEbUyvzz1T02Qxko+fvvDK+ipySv68cvB+LDxa3wY//bLP79/uJD9+UN/F2kS/6X+Nf26tE+v+szLQvpECFZhjAb2AsWNtJUeDCbmk3gudTGNGJrln60guFfMwKmeE54gv/3jb0dujGtm82DmhO0rFQarTgCW/LZB/FomGX63IVGxIVGHXYZOYCsMiDxGpr6/fc0MU5riHxcpYSvOyj9zEPw2UvQUtYC+dwK4QVk2DKZafjhKEGI89nqE7J7nNyOv5cyUtwcQ9KjAJOQTMbzVCbMiv5F+E0i8dtu8zL0cAYYRd+pJj5D/P0sOlgrT558eCLUlv4wKeC7GMOXDcpt2wYxvDxNxiNB02OEmh+xX9DzM4+Y939uHr36yD8P//OsFkiQPBrOon28pVB/w7OH46ZOQrUmNxY89D73sp/pVJ8OEd8wM8Kdh37+s91+/ev3Nmz+9+e7tuz98/90/vX796rvv333z8u13b9988927tz88LLWKxv7pNCY7FUJMTHhXgFqqZ3pOYRX+WYNOVVGGKv4wMDFuD4kc2IxsCOv+G+4fXn7/5tXLV5/B/uOfv3nz6g6TP0apMxIlUNAgmHmhd5NhaHvi9yh+GN+bf9zNs6Di0tHTufkvmL74n/8Fl+eKoQ==")))
MANIFEST = json.loads(zlib.decompress(base64.b64decode("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")))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write_json(p, d):
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False, allow_nan=False))


def prepare(t, tf):
    """Fixed left-closed UTC bars; time = start; decisions at end."""
    sec = tf * 60
    q = t.assign(bucket=t.ts_utc_ns // (sec * NS))
    q = q.assign(pv=q.price_ticks * q.volume)
    b = q.groupby("bucket", sort=True).agg(
        o=("price_ticks", "first"), h=("price_ticks", "max"),
        l=("price_ticks", "min"), c=("price_ticks", "last"),
        v=("volume", "sum"), pv=("pv", "sum"), n=("volume", "size")
    ).reset_index()
    b["close_ns"] = (b.bucket + 1) * sec * NS
    et = pd.to_datetime(b.bucket * sec * NS, utc=True).dt.tz_convert("America/New_York")
    b["date_et"] = et.dt.strftime("%Y%m%d")
    b["minute"] = et.dt.hour * 60 + et.dt.minute
    tr = np.maximum(b.h - b.l, np.maximum(abs(b.h - b.c.shift()), abs(b.l - b.c.shift())))
    b["atr_prev"] = tr.rolling(20, min_periods=20).mean().shift(1)
    # No estimate across an unobserved bar.
    consecutive = b.bucket.diff().eq(1).rolling(20, min_periods=20).sum().eq(20)
    b.loc[~consecutive, "atr_prev"] = np.nan
    return b


def signals(b, day, family, tf):
    """Returns only causal signal-close time and direction; no future labels."""
    r = (b.date_et == day) & b.minute.ge(570) & b.minute.lt(960)
    rb = b.loc[r]
    expected_minutes = list(range(570, 960, tf))
    if rb.minute.tolist() != expected_minutes:
        return [], "INCOMPLETE_RTH_BARS"
    vwap = rb.pv.cumsum() / rb.v.cumsum()
    range30 = rb[rb.minute < 600]
    hi, lo = float(range30.h.max()), float(range30.l.min())
    ev, blocked_until, breakout = [], -1, None
    for idx, row in rb.iterrows():
        # Last decision 13:45, so a full two-hour exit fits within RTH.
        if row.minute < 600 or row.minute + tf > 825:
            continue
        if int(row.close_ns) <= blocked_until:
            continue
        direction = 0
        if family == "MOM60":
            lag = 60 // tf
            if idx >= lag and b.bucket.iloc[idx] - b.bucket.iloc[idx-lag] == lag:
                move = row.c - b.c.iloc[idx-lag]
                if np.isfinite(row.atr_prev) and abs(move) >= row.atr_prev:
                    direction = int(np.sign(move))
        elif family == "VWAP2":
            move = row.c - vwap.loc[idx]
            if np.isfinite(row.atr_prev) and abs(move) >= 2 * row.atr_prev:
                direction = -int(np.sign(move))
        else:
            if breakout is None:
                if row.c >= hi + 1:
                    breakout = (int(row.close_ns), 1)
                elif row.c <= lo - 1:
                    breakout = (int(row.close_ns), -1)
            elif int(row.close_ns) - breakout[0] <= 30 * 60 * NS:
                if lo <= row.c <= hi:
                    direction = -breakout[1]
            else:
                break  # first breakout only, no retry
        if direction:
            ev.append((int(row.close_ns), direction))
            # Add 1s to ensure no next-bar duplicate under 250ms entry latency.
            blocked_until = int(row.close_ns) + 7201 * NS
            if family == "ORFAIL30":
                break
    return ev, "PASS"


def outcome(t, signal_ns, d):
    ts = t.ts_utc_ns.to_numpy()
    # Use first observed tick strictly after decision +250ms.
    e = int(np.searchsorted(ts, signal_ns + 250_000_000, side="right"))
    if e >= len(ts) or ts[e] > signal_ns + 1_000_000_000:
        return None, "ENTRY_LATE_OR_MISSING"
    x = int(np.searchsorted(ts, ts[e] + 7200 * NS, side="left"))
    if x >= len(ts) or ts[x] > ts[e] + 7201 * NS:
        return None, "EXIT_LATE_OR_MISSING"
    a, b = t.iloc[e], t.iloc[x]
    if not np.isfinite([a.bid_ticks,a.ask_ticks,b.bid_ticks,b.ask_ticks]).all():
        return None, "QUOTE_MISSING"
    if not (0 < a.bid_ticks < a.ask_ticks and 0 < b.bid_ticks < b.ask_ticks):
        return None, "QUOTE_INVALID"
    if d == 1:
        ep, xp = float(a.ask_ticks), float(b.bid_ticks)
        reverse = float(a.bid_ticks - b.ask_ticks)
    else:
        ep, xp = float(a.bid_ticks), float(b.ask_ticks)
        reverse = float(b.bid_ticks - a.ask_ticks)
    gross = d * (xp - ep)
    baseline = (gross + reverse) / 2
    net = gross - 2 * SLIP_SIDE - COMMISSION
    alpha = gross - baseline
    # Independent midquote direction check, not the execution algebra above.
    mid_change = ((b.bid_ticks + b.ask_ticks) - (a.bid_ticks + a.ask_ticks)) / 2
    assert abs(alpha - d * mid_change) < 1e-10
    # Reference sum of entry/exit cash flows, independently signed.
    ref = (float(b.bid_ticks) - float(a.ask_ticks) if d > 0
           else float(a.bid_ticks) - float(b.ask_ticks)) - 2.9
    assert abs(net - ref) < 1e-10
    return dict(signal_ns=signal_ns, entry_ns=int(ts[e]), exit_ns=int(ts[x]),
                direction=d, entry_quote=ep, exit_quote=xp, gross=gross, net=net,
                alpha=alpha, baseline_gross=baseline), "PASS"


def evaluate(rows, days, seed, n_tests=12):
    """Equal resampling of CME sessions; ratio = total PNL / total trades."""
    g = pd.DataFrame(rows)
    if g.empty:
        return {"status": "INCONCLUSIVE_SAMPLE", "trades": 0, "active_sessions": 0}
    grouped = g.groupby("day").agg(net=("net", "sum"), alpha=("alpha", "sum"),
                                    n=("net", "size")).reindex(days, fill_value=0)
    a = grouped[["net", "alpha", "n"]].to_numpy(float)
    n, active = int(a[:,2].sum()), int((a[:,2] > 0).sum())
    out = dict(trades=n, active_sessions=active, eligible_sessions=len(days),
               net_ticks=float(a[:,0].sum()/n), alpha_ticks=float(a[:,1].sum()/n),
               net_ticks_per_eligible_session=float(a[:,0].mean()))
    if n < 30 or active < 20:
        return dict(out, status="INCONCLUSIVE_SAMPLE")
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(20):
        ix = rng.integers(0, len(a), size=(BOOT//20, len(a)))
        sums = a[ix].sum(axis=1)
        values.append(sums[sums[:,2] > 0,:2] / sums[sums[:,2] > 0,2,None])
    boot = np.vstack(values)
    low = np.quantile(boot, .05/n_tests, axis=0)
    high = np.quantile(boot, .95, axis=0)
    se = boot.std(axis=0, ddof=1)
    mde = (norm.ppf(1-.05/n_tests)+norm.ppf(.8))*se
    out.update(lower_bonferroni=low.tolist(), upper_one_sided95=high.tolist(),
               mde80_ticks=mde.tolist(), bootstrap_sessions=BOOT,
               net_adverse_ticks=out["net_ticks"]-2,  # +1 extra slip per side
               status="SCREEN_PASS" if bool((low > 0).all()) else "NO_SUPPORT")
    # Independent table-free aggregation of headline values.
    assert abs(out["net_ticks"] - sum(x["net"] for x in rows)/len(rows)) < 1e-9
    assert abs(out["alpha_ticks"] - sum(x["alpha"] for x in rows)/len(rows)) < 1e-9
    return out


def selftest():
    # Raw quote fills / strict latency / first tick at target.
    t = pd.DataFrame(dict(ts_utc_ns=[0,250_000_000,500_000_000,7200*NS+500_000_000],
                          bid_ticks=[99,99,100,110], ask_ticks=[101,101,102,112]))
    o,r = outcome(t,0,1)
    assert r == "PASS" and o["entry_ns"] == 500_000_000 and o["net"] == 5.1
    o,r = outcome(t,0,-1)
    assert r == "PASS" and o["net"] == -14.9
    bad=t.copy(); bad.loc[3,"bid_ticks"]=113
    assert outcome(bad,0,1)[1] == "QUOTE_INVALID"
    assert outcome(t,1_000_000_000,1)[1] == "ENTRY_LATE_OR_MISSING"
    # Build full session fixture, perturb future bars, compare known signals.
    n=23*60
    start=pd.Timestamp("2025-10-07 17:00",tz="America/Chicago").value
    ts=start+np.arange(n)*60*NS
    p=1000+((np.arange(n)//30)%10)
    f=pd.DataFrame(dict(ts_utc_ns=ts, price_ticks=p, volume=np.ones(n)))
    for tf in (5,15):
        b=prepare(f,tf)
        for fam in ("MOM60","VWAP2","ORFAIL30"):
            sig,reason=signals(b,"20251008",fam,tf)
            assert reason == "PASS"
            cut=pd.Timestamp("2025-10-08 12:00",tz="America/New_York").value
            changed=b.copy()
            future=changed.close_ns>cut
            changed.loc[future,["o","h","l","c","pv"]]=1e6
            sig2,_=signals(changed,"20251008",fam,tf)
            assert [e for e in sig if e[0]<=cut] == [e for e in sig2 if e[0]<=cut]
    rows=[dict(day=f"d{i}",net=1.,alpha=2.) for i in range(30)]
    assert evaluate(rows,[f"d{i}" for i in range(30)],1)["status"] == "SCREEN_PASS"
    assert evaluate(rows[:5],[f"d{i}" for i in range(30)],1)["status"] == "INCONCLUSIVE_SAMPLE"
    return {"checks": "quotes_latency_time_exit_gap_prefix_6cells_inference_counts",
            "status": "PASS"}


def run(input_dir, out):
    out.mkdir(parents=True,exist_ok=True)
    write_json(out/"manifest.json",MANIFEST)
    write_json(out/"selftests.json",selftest())
    catpath = input_dir/"catalogs/RTY_nt8_2025_2026q3_sessions_catalog.json"
    assert sha(catpath) == EXPECTED["catalogs/RTY_nt8_2025_2026q3_sessions_catalog.json"]
    actualcat=json.loads(catpath.read_text())
    assert actualcat == CATALOG
    auditpath=input_dir/"AUDIT_MANIFEST.json"
    assert sha(auditpath)==EXPECTED["AUDIT_MANIFEST.json"]
    audit=json.loads(auditpath.read_text())
    assert audit["compression"]=="zstd:19"
    audit_files={x["relative_path"]:x for x in audit["files"]}
    sessions=[s for s in CATALOG["sessions"] if s["trade_date"]<=END]
    assert len({s["trade_date"] for s in sessions}) == len(sessions)
    assert all(s["end"] < HOLDOUT and s["start"] < s["end"] for s in sessions)
    byfile={}
    for s in sessions:
        byfile.setdefault(PureWindowsPath(s["path"]).name,[]).append(s)
    provenance=[]
    # Hash complete containers for custody; only selected pre-April row groups
    # are decoded. Hashing bytes does not inspect post-boundary outcomes.
    for name,ss in byfile.items():
        f=input_dir/"RTY"/name
        assert sha(f)==EXPECTED["RTY/"+name], ("FILE_HASH",name)
        mpath=f.with_name(name.replace("_ticks_ext.parquet","_manifest_ext.json"))
        assert sha(mpath)==EXPECTED["RTY/"+mpath.name]
        m=json.loads(mpath.read_text()); meta=pq.ParquetFile(f)
        af=audit_files["RTY/"+name]
        assert af["sha256"]==EXPECTED["RTY/"+name]
        assert af["rows"]==meta.metadata.num_rows and af["size_zstd_bytes"]==f.stat().st_size
        assert m["rows"]==meta.metadata.num_rows and m["tick_size"]==.1
        assert m["contract"]==ss[0]["contract"]
        provenance.append(dict(name=name,sha256=sha(f),rows=meta.metadata.num_rows,
                               upstream_pre_recompression_sha=m["parquet_sha256"]))
    write_json(out/"preflight.json",dict(provenance=provenance,sessions=len(sessions),
               source_catalog_sha=sha(catpath), holdout_opened=False,
               validation_outcomes_opened=False, l2_used=False,
               executed_script_sha256=sha(Path(__file__)),python=platform.python_version(),
               pandas=pd.__version__,numpy=np.__version__,audit_manifest_sha=sha(auditpath)))
    ledger={f"{fam}_{tf}": [] for fam,tf in CELLS}
    decisions=[]
    cache={}
    # Only discovery initially: no validation price labels yet.
    def process(selected, phase, permitted):
        for name in byfile:
            ss=[s for s in selected if PureWindowsPath(s["path"]).name==name]
            if not ss:
                continue
            f=input_dir/"RTY"/name
            cols=["ts_utc_ns","price_ticks","bid_ticks","ask_ticks","volume"]
            lo,hi=min(s["start"] for s in ss),max(s["end"] for s in ss)
            # Arrow predicate pushdown, followed by exact session cuts.
            t=pd.read_parquet(f, columns=cols, filters=[("ts_utc_ns",">=",lo),("ts_utc_ns","<",hi)])
            assert not t[["ts_utc_ns","price_ticks","volume"]].isna().any().any()
            assert t.ts_utc_ns.is_monotonic_increasing
            assert (t.price_ticks>0).all() and (t.volume>0).all()
            assert np.equal(t.price_ticks,np.floor(t.price_ticks)).all()
            ts=t.ts_utc_ns.to_numpy()
            for s in ss:
                l,r=np.searchsorted(ts,[s["start"],s["end"]],side="left")
                g=t.iloc[l:r].reset_index(drop=True)
                assert len(g)==s["ticks"],("CATALOG_COUNT",s["trade_date"],len(g),s["ticks"])
                et=pd.to_datetime(g.ts_utc_ns,utc=True).dt.tz_convert("America/New_York")
                mask=(et.dt.strftime("%Y%m%d")==s["trade_date"]) & (et.dt.hour*60+et.dt.minute>=570) & (et.dt.hour*60+et.dt.minute<960)
                rt=g.loc[mask]
                gap=float(rt.ts_utc_ns.diff().max()/NS) if len(rt)>1 else 1e99
                gate=bool(len(rt)>0 and gap<=60)
                for tf in (5,15):
                    b=prepare(g,tf)
                    for fam in ("MOM60","VWAP2","ORFAIL30"):
                        key=f"{fam}_{tf}"
                        if key not in permitted: continue
                        ev,reason=signals(b,s["trade_date"],fam,tf)
                        d=dict(day=s["trade_date"],contract=s["contract"],phase=phase,cell=key,
                               signals=0,trades=0,censored={},rth_gap_s=gap,
                               status=reason if gate else "RTH_GAP_OR_EMPTY")
                        if gate and reason=="PASS":
                            d["signals"]=len(ev)
                            for ns,side in ev:
                                o,why=outcome(g,ns,side)
                                if o is None:
                                    d["censored"][why]=d["censored"].get(why,0)+1
                                else:
                                    o.update(day=s["trade_date"],contract=s["contract"],cell=key,phase=phase)
                                    ledger[key].append(o);d["trades"]+=1
                        assert d["signals"]==d["trades"]+sum(d["censored"].values())
                        decisions.append(d)
                if len(decisions)%30==0:
                    print("progress",phase,s["trade_date"],flush=True)
            del t
    discovery=[s for s in sessions if s["trade_date"]<=DISC_END]
    process(discovery,"discovery",set(ledger))
    result={}
    for j,key in enumerate(ledger):
        days=[d["day"] for d in decisions if d["cell"]==key and d["status"]=="PASS"]
        result[key]=dict(discovery=evaluate(ledger[key],days,SEED+j,n_tests=12))
    survivors=[key for key,v in result.items() if v["discovery"]["status"]=="SCREEN_PASS"]
    if survivors:
        process([s for s in sessions if s["trade_date"]>DISC_END],"validation",set(survivors))
        for j,key in enumerate(survivors):
            rows=[r for r in ledger[key] if r["phase"]=="validation"]
            days=[d["day"] for d in decisions if d["phase"]=="validation" and d["cell"]==key and d["status"]=="PASS"]
            result[key]["validation"]=evaluate(rows,days,SEED+100+j,n_tests=2*len(survivors))
    for key in result:
        if key not in survivors:
            result[key]["validation"]={"status":"NOT_OPENED_DISCOVERY_GATE"}
    # Private ledgers stay in private Kaggle output; do not push these to Git.
    pd.DataFrame([r for v in ledger.values() for r in v]).to_csv(out/"trades_PRIVATE.csv",index=False)
    pd.DataFrame(decisions).to_json(out/"decisions_PRIVATE.jsonl",orient="records",lines=True)
    write_json(out/"results.json",dict(cells=result,discovery_survivors=survivors,
               l2_used=False,holdout_opened=False,validation_outcomes_opened=bool(survivors),
               status="EXPLORATORY_SCREEN_NOT_LIVE_OR_HOLDOUT_CONFIRMED",
               costs="Observed bid/ask at ticks, 1 tick slippage/side + assumed USD4.50 RT",
               limits=["Quote exports are not order fills or certified quote age",
                       "Prior research exposure means development is not virgin",
                       "Bootstrap sessions is not a live execution certification"]))
    print(json.dumps(result,indent=2),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--input");p.add_argument("--out",default="/kaggle/working/rty_no_l2");p.add_argument("--selftest",action="store_true")
    a=p.parse_args()
    if a.selftest: print(selftest())
    else:
        if a.input:
            root=Path(a.input)
        else:
            matches=list(Path("/kaggle/input").rglob("RTY_nt8_2025_2026q3_sessions_catalog.json"))
            assert len(matches)==1,("DATASET_ROOT",len(matches))
            root=matches[0].parent.parent
        run(root,Path(a.out))