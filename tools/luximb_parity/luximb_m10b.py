"""M10b: H3 controlando por cobertura previa de las franjas (precio ya visitado). Ver enmienda M10b en el manifiesto M10.
Uso: python tools/luximb_parity/luximb_m10b.py <out.json>"""
import glob
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import luximb_m10 as M  # noqa: E402

REPO = HERE.parents[1]; BUN = REPO / "viewer/nt8_bridge/bundles"
D10 = REPO / "docs/research/luximb_parity_20261020/desc_m10"; D8 = REPO / "docs/research/luximb_parity_20261020/desc_m8"


def features(a):
    if a in ("NQ", "ES"):
        imps = sorted(glob.glob(str(D8 / f"imp_{a}_*.json"))); out = D8 / f"featcob_{a}.csv"
        trip = [f"{a}:{(BUN / (a + '_' + Path(p).stem.split('_', 2)[2] + '_M1_LUXIMB.json')).relative_to(REPO).as_posix()}:{Path(p).relative_to(REPO).as_posix()}" for p in imps]
    else:
        ids = sorted(Path(p).stem.replace("impA_", "") for p in glob.glob(str(D10 / f"impA_{a}_*.json"))); out = D10 / f"featcob_{a}.csv"
        trip = [f"{a}:{(BUN / (i + '.json')).relative_to(REPO).as_posix()}:{(D10 / ('impA_' + i + '.json')).relative_to(REPO).as_posix()}" for i in ids]
    if not out.exists():
        subprocess.run([sys.executable, "-X", "utf8", str(HERE / "luximb_m8_features.py"), out.relative_to(REPO).as_posix()] + trip, check=True, cwd=REPO)
    return pd.read_csv(out)


def main():
    rng = np.random.default_rng(20261029); res = {}
    for a in ("MYM", "GC", "6E", "6B", "6J", "MBT", "NQ", "ES"):
        f = features(a); f = f[f.vol_pre.notna() & f.cob_ad.notna()].copy()
        lo, hi = np.quantile(f.D_200, [.2, .8])
        f["g"] = np.where(f.D_200 >= max(hi, 1e-9), 1, np.where(f.D_200 <= min(lo, -1e-9), 0, -1))
        base = M.estr(f, [("vol_pre", [.2, .4, .6, .8]), ("R", [1 / 3, 2 / 3])]) + f.cash.map({True: "c", False: "r"})
        f["estr"] = base; r_sin = M.boot_dif(f, "y1_tg", "g", rng)
        f["estr"] = base + M.estr(f, [("cob_ad", [1 / 3, 2 / 3]), ("cob_at", [1 / 3, 2 / 3])]); r_con = M.boot_dif(f, "y1_tg", "g", rng)
        g = f[f.g >= 0]
        res[a] = dict(H3_sin_cobertura=r_sin, H3b_con_cobertura=r_con,
                      cobertura_media_adelante_g1_g0=[round(float(g.loc[g.g == 1, "cob_ad"].mean()), 3), round(float(g.loc[g.g == 0, "cob_ad"].mean()), 3)],
                      cobertura_media_atras_g1_g0=[round(float(g.loc[g.g == 1, "cob_at"].mean()), 3), round(float(g.loc[g.g == 0, "cob_at"].mean()), 3)])
        print(a, r_sin and (r_sin["est"], r_sin["ic95"]), r_con and (r_con["est"], r_con["ic95"]), res[a]["cobertura_media_adelante_g1_g0"], flush=True)
    xs = [res[a]["H3b_con_cobertura"] for a in ("MYM", "GC", "6E", "6B", "6J", "MBT") if res[a]["H3b_con_cobertura"]]
    w = np.array([1 / x["se"] ** 2 for x in xs]); e = np.array([x["est"] for x in xs]); est = float((w * e).sum() / w.sum()); se = float(np.sqrt(1 / w.sum()))
    comb = dict(est=round(est, 4), se=round(se, 4), ic95=[round(est - 1.96 * se, 4), round(est + 1.96 * se, 4)], p=float(2 * norm.sf(abs(est / se))),
                negativos=int((e < 0).sum()), activos=len(xs))
    json.dump(dict(enmienda="M10b", por_activo=res, combinado_6_activos_H3b=comb), open(sys.argv[1], "w", encoding="utf-8"), indent=1, default=str)
    print(json.dumps(comb))


if __name__ == "__main__":
    main()
