"""Kernel de Kaggle: ideas de la literatura (edgelab/research/macro_literatura.py) sobre barras de Dukascopy exportadas de SQX, con el
nulo de la búsqueda (familia completa sobre series sintéticas). Lo arma tools/macro_literatura.py (código del módulo incrustado)."""
import glob, json, os, time
import numpy as np, pandas as pd
ML = __import__("macro_literatura")
t0 = time.time(); ent = os.environ.get("ENTRADA", "/kaggle/input")
D1 = {os.path.basename(p)[:-7]: ML.leer(p) for p in glob.glob(ent + "/**/*_D1.csv", recursive=True)}
H1 = {os.path.basename(p)[:-7]: ML.leer(p) for p in glob.glob(ent + "/**/*_H1.csv", recursive=True)}
SPREADS = json.loads(open(glob.glob(ent + "/**/spreads.json", recursive=True)[0]).read())
F = ML.familia(D1, H1, SPREADS); F.update(ML.canastas(F))
res = {k: ML.por_periodo(v) for k, v in F.items()}
FB = ML.familia(D1, H1, {}); FB.update(ML.canastas(FB)); res_bruto = {k: ML.por_periodo(v) for k, v in FB.items()}   # sin spread: señal vs fricción
def tmax(F, per="DESC"):
    ts = [ML.por_periodo(v)[per]["t"] for v in F.values() if len(v)]
    return max([t for t in ts if t is not None], default=float("nan"))
nulos = []
for s in range(int(os.environ.get("REPS", "200"))):
    D1s = {k: ML.sintetica(v, 1000 + s) for k, v in D1.items()}; H1s = {k: ML.sintetica(v, 2000 + s) for k, v in H1.items()}
    Fs = ML.familia(D1s, H1s, SPREADS); Fs.update(ML.canastas(Fs)); nulos.append(tmax(Fs))
    if s % 20 == 0: print(f"[{time.time() - t0:6.0f}s] nulo {s}", flush=True)
umbral = float(np.nanpercentile(nulos, 95))
json.dump(dict(variantes=res, variantes_bruto=res_bruto, nulo_tmax_desc=nulos, umbral_p95_desc=umbral, activos_d1=sorted(D1), activos_h1=sorted(H1),
               segundos=round(time.time() - t0)), open("RESULTADO.json", "w"), indent=1, default=float)
print("listo", len(F), "variantes; umbral p95 t DESC", round(umbral, 2))
