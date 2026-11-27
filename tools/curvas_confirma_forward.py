"""Curvas de las canastas que confirman en HOLDOUT A5 o van a forward (lee series ya publicadas; no abre nada). Uso: PYTHONPATH=. python tools/curvas_confirma_forward.py"""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from edgelab.holdout import a5_bloque
R="docs/research/"; OUT=R+"curvas_forward_20261127/"
M=pd.read_csv(R+"holdout_a5_nocme_20261127/SERIES_HOLDOUT_A5_NOCME_MENSUAL.csv.gz",index_col=0)
M.index=pd.PeriodIndex(M.index,freq="M").to_timestamp(how="end").normalize()
def norm(s):
    s=s.dropna(); sd=s[M.loc[s.index,"bloque"]=="DESC"].std()
    return s/(sd*np.sqrt(12))*10
def stats(s,b):
    x=s[M.loc[s.index,"bloque"]==b]; return len(x), x.mean()/x.std()*np.sqrt(12), x.mean()/x.std()*np.sqrt(len(x))
C={"azul":"#2a6fdb","naranja":"#e07b25","verde":"#2e9e5b","gris":"#8a8f98","rojo":"#c8433a"}
fig,ax=plt.subplots(4,1,figsize=(12,17),facecolor="white")
def sombrear(a,ini,fin):
    for t,b in M["bloque"].items():
        if b=="HOLDOUT" and ini<=t<=fin: a.axvspan(t-pd.offsets.MonthBegin(1),t,color="#f2d7a6",alpha=.45,lw=0)
def panel(a,cols,titulo,ini,nota):
    sombrear(a,pd.Timestamp(ini),pd.Timestamp("2026-09-30"))
    for (c,lab,col) in cols:
        s=norm(M[c]); s=s[s.index>=ini]; a.plot(s.index,s.cumsum(),color=col,lw=2,label=lab)
        n,sr,t=stats(norm(M[c]),"HOLDOUT"); a.annotate(f"{lab}: HOLDOUT {n} m, SR {sr:.2f}, t {t:.2f}",xy=(0.01,0.93-0.07*cols.index((c,lab,col))),xycoords="axes fraction",fontsize=9,color=col)
    a.set_title(titulo,loc="left",fontsize=12,fontweight="bold"); a.set_ylabel("% acumulado a 10 % vol anual")
    a.grid(alpha=.25); a.legend(loc="lower right",fontsize=9); a.text(0.99,0.97,nota,transform=a.transAxes,ha="right",va="top",fontsize=8,color="#555")
    for s in ("top","right"): a.spines[s].set_visible(False)
panel(ax[0],[("Carril2_Sell16","Carril 2 sellada (16)",C["azul"]),("Pool_NoCME_Dyn_4F_63m","Pozo sin CME (4 frentes)",C["naranja"])],
      "1. CONFIRMA en HOLDOUT A5 — Carril 2 sellada y pozo (swing, requiere mantener de noche)","2006-01-01","Bandas: meses HOLDOUT A5 (sellados hasta hoy). Pesos y reglas congelados en DESC.")
panel(ax[1],[("Macro_RP_Canasta","Macro risk premia (RP4 tasas/crédito)",C["verde"])],
      "2. NO_CONCLUYENTE, va a forward — Macro risk premia (ETFs)","2006-01-01","Potencia previa 0,11–0,21: su holdout no podía decidir.")
panel(ax[2],[("Cripto_v3_Canasta","Cripto v3 (XSMOM+BetaNeut+BAB)",C["azul"]),("Cripto_OFI_Canasta","Cripto flujo taker (OFI)",C["rojo"])],
      "3. NO_CONCLUYENTE, va a forward — Cripto perpetuos Binance (20 pb + funding)","2021-01-01","REP de cripto v3 iterada (v1→v3): sólo HOLDOUT es limpio.")
S=pd.read_csv(R+"estabilidad_cartera_20261126/SERIES_DIARIAS.csv.gz",index_col=0,parse_dates=True)
S=S[S.index<"2026-10-01"].fillna(0)
a=ax[3]; b=pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in S.index],index=S.index)
for t in M.index[(M["bloque"]=="HOLDOUT")&(M.index>="2019-07-01")]: a.axvspan(t-pd.offsets.MonthBegin(1),t,color="#f2d7a6",alpha=.45,lw=0)
for cols,lab,col in [(["T_NQ","R_NQ"],"T + R (canasta forward pre-registrada)",C["azul"]),(["T_NQ","R_NQ","Z_NQ"],"T + R + Z",C["naranja"]),(["T_NQ","R_NQ","Z_NQ","V_NQ"],"T + R + Z + V",C["verde"])]:
    a.plot(S.index,S[cols].sum(axis=1).cumsum(),color=col,lw=1.8,label=lab)
a.set_title("4. En forward desde 2026-11-14 — intradía NQ (FundedSync, 1 micro c/u, USD)",loc="left",fontsize=12,fontweight="bold")
a.set_ylabel("USD acumulados (1 micro)"); a.grid(alpha=.25); a.legend(loc="upper left",fontsize=9)
for s in ("top","right"): a.spines[s].set_visible(False)
a.text(0.99,0.02,"El vendedor vio 2020→2026-08: esta historia no es evidencia fuera de muestra.\nForward 14→23-nov: T +3,4 R (5 op), R −1,0 R (1), canasta T+R +2,4 R (6); e-proceso SIN_DECIDIR.",transform=a.transAxes,ha="right",va="bottom",fontsize=8,color="#555")
fig.suptitle("EdgeLab — curvas que confirman o van a forward (datos hasta 2026-09-30; TERMINAL sellado)",fontsize=14,fontweight="bold",y=0.995)
fig.tight_layout(rect=(0,0,1,0.985)); fig.savefig(OUT+"CURVAS_CONFIRMA_Y_FORWARD.png",dpi=130)
print("ok")
