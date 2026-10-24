"""Prueba pre-registrada (`docs/research/luximb_parity_20261020/PREREGISTRO_VI_COINCIDENTES_REACCION_20261022.md`): ¿los VI del
futuro NQ que también nacen en el índice USATECH reaccionan más a 30 min, controlando tamaño, hora y dirección?
Una sola prueba (contador: luximb_20261022/vi_coincidentes_reaccion30_rep). No cambiar después de mirar.

  python tools/luximb_parity/vi_coincidentes_reaccion_rep.py <bundle_cfd> <out.json> <bundle_fut> [<bundle_fut> ...]
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
import comparar_zonas_futuro_vs_cfd as C  # noqa: E402
import comportamiento_coincidentes as K  # noqa: E402

FRICCION = 1.545            # edgelab.costos.friccion_rt_puntos("NQ")
B, SEED = 4000, 20261022


def trade_date(ts):
    t = pd.DatetimeIndex(pd.to_datetime(np.asarray(ts), unit="s", utc=True)).tz_convert("America/Chicago") + pd.Timedelta(hours=7)
    return np.asarray(t.strftime("%Y%m%d"), dtype=int)


def main():
    pc, out, futs = sys.argv[1], sys.argv[2], sys.argv[3:]
    filas = []
    for pf in futs:
        Bf = json.load(open(pf, encoding="utf-8")); w0, w1 = Bf["meta"]["ventana_trade_date"]
        a = int(pd.Timestamp(str(w0), tz="UTC").timestamp()) - 2 * 86400; b = int(pd.Timestamp(str(w1), tz="UTC").timestamp()) + 2 * 86400
        cf, zf = C.cargar(pf, a, b); cc, zc = C.cargar(pc, a, b)
        zf = zf[(trade_date(zf.t0) >= w0) & (trade_date(zf.t0) <= w1)].reset_index(drop=True)
        com = cf.index.intersection(cc.index)
        base = (cf.close.loc[com] - cc.close.loc[com]).rolling(240, min_periods=30, center=True).median()
        base = base.reindex(sorted(set(cf.index) | set(cc.index))).interpolate().ffill().bfill()
        co = K.emparejar(zf, zc, base)
        M = K.medir(zf, pd.DataFrame(Bf["bar_series"]["time_1m"]["candles"]).set_index("time"))
        vi = (zf.label == "VI").to_numpy()
        d = pd.DataFrame(dict(reac30=M.reac30.to_numpy()[vi], co=co[vi].astype(float), logh=np.log(zf.height_ticks.to_numpy()[vi]),
                              hora=pd.to_datetime(zf.t0[vi], unit="s", utc=True).dt.hour.to_numpy(), bull=(zf.dir[vi] == "BULL").to_numpy().astype(float),
                              dia=trade_date(zf.t0[vi]), contrato=Bf["meta"]["contract"]))
        filas.append(d); print(pf.split("/")[-1], "VI", int(vi.sum()), "coincidentes", int(co[vi].sum()), "base mediana", round(float(np.nanmedian(base)), 1), flush=True)
    D = pd.concat(filas, ignore_index=True).dropna(subset=["reac30"])
    X = np.column_stack([np.ones(len(D)), D.co, D.logh, D.bull] + [(D.hora == h).astype(float) for h in range(1, 24)])
    y = D.reac30.to_numpy(); coef = lambda Xs, ys: np.linalg.lstsq(Xs, ys, rcond=None)[0][1]
    obs = coef(X, y); dias = D.dia.to_numpy(); u = np.unique(dias); ix = {k: np.flatnonzero(dias == k) for k in u}; rng = np.random.default_rng(SEED); bs = []
    for _ in range(B):
        s = np.concatenate([ix[k] for k in rng.choice(u, len(u))]); bs.append(coef(X[s], y[s]))
    bs = np.array(bs); p = float((bs <= 0).mean()); ic = [float(np.quantile(bs, .05)), float(np.quantile(bs, .95))]
    se = float(bs.std(ddof=1)); mde = 2.486 * se                      # (z_0,95 + z_0,80) * se
    estado = "CONFIRMA" if (p <= 0.05 and obs > FRICCION) else ("REFUTA" if ic[1] < FRICCION else "SIN_POTENCIA")
    g = D.co == 1
    res = dict(prereg="docs/research/luximb_parity_20261020/PREREGISTRO_VI_COINCIDENTES_REACCION_20261022.md", n_vi=int(len(D)), n_coincidentes=int(g.sum()),
               dias=int(len(u)), media_coincidentes=float(D.reac30[g].mean()), media_no=float(D.reac30[~g].mean()), dif_cruda=float(D.reac30[g].mean() - D.reac30[~g].mean()),
               coef_controlado=float(obs), ic90=ic, p_unilateral=p, se=se, mde_80=mde, friccion_pts=FRICCION, estado=estado,
               n_necesario_para_coef_observado=(int(np.ceil(len(D) * (2.486 * se / obs) ** 2)) if obs > 0 else None),
               por_contrato={c: dict(n=int(len(x)), coinc=int((x.co == 1).sum()), dif=float(x.reac30[x.co == 1].mean() - x.reac30[x.co == 0].mean()))
                             for c, x in D.groupby("contrato")})
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
