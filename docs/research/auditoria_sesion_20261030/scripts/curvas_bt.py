import json,polars as pl,datetime as dt
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fs=sorted(Path("bt_res").glob("*.json")); cols=[]
fig,axs=plt.subplots(2,1,figsize=(12,9)); corte=dt.datetime(2026,4,1); rec=dt.datetime(2026,1,1)
for f in fs:
    o=json.load(open(f))["operaciones"]
    df=pl.DataFrame({"neto":o["neto"],"t":o["t"]}).with_columns(pl.from_epoch("t",time_unit="s").alias("ts")).sort("ts")
    sd=df.filter(pl.col("ts")<corte)["neto"].std(); df=df.with_columns((pl.col("neto")/sd).alias("r"),pl.col("neto").cum_sum().alias("eq")); df=df.with_columns(pl.col("r").cum_sum().alias("eqr"))
    axs[0].plot(df["ts"].to_list(),df["eqr"].to_list(),label=f"{f.stem} (n={len(df)})",lw=1.3); cols.append(df.select("ts","r"))
b=pl.concat(cols).sort("ts").with_columns(pl.col("r").cum_sum().alias("eq"))
axs[1].plot(b["ts"].to_list(),b["eq"].to_list(),color="k",lw=1.6,label=f"Canasta riesgo igual ({len(fs)} reglas, n={len(b)})")
for a in axs:
    a.axvline(corte,color="r",ls="--",label="DESC | OOS (01/04)"); a.axvline(rec,color="gray",ls=":",label="canal reciente (01/01)"); a.axhline(0,color="gray",lw=.5); a.legend(fontsize=8); a.grid(alpha=.3); a.set_ylabel("R acumulado (neto / sd de la regla)")
axs[0].set_title("Reglas con acta: equity neta sobre DESC+OOS (sin holdout)"); axs[1].set_title("Canasta con pesos de riesgo iguales")
plt.tight_layout(); plt.savefig("equity_actas.png",dpi=110); print(len(fs),len(b))
s=b.filter(pl.col("ts")>=corte)["r"]; print("canasta OOS n",len(s),"media r",round(s.mean(),3),"se",round(s.std()/len(s)**.5,3))
