#!/usr/bin/env python3
"""Selección de datos APROBADOS para análisis: aplica reglas fijas, por sesión, al catálogo y escribe docs/data_catalog/{curated.json,CURATED.md,REEXPORT.md}.
Reglas (iguales para todos los instrumentos; se cambian solo en este archivo y se documentan):
  1. Serie líder y elegibilidad del catálogo (mayor volumen de la sesión anterior; volumen >= 50 % de la mediana del contrato).
  2. Excluida si el volumen es < 25 % de la mediana de volumen del líder de TODO el instrumento (liquidez baja respecto del instrumento).
  3. Excluida si tiene menos de la mitad de los minutos típicos (sesión truncada o cierre temprano).
  4. Con salvedad (no excluida) si el contrato tiene fuentes en conflicto material (> 1 % de diferencia de trades en más del 10 % de los días comunes).
  5. Excluida toda sesión desde 2026-10-01 (holdout formal).
Veredicto por instrumento: APROBADO (>= 85 % de las sesiones elegibles aprobadas y sin salvedades), CON_SALVEDADES (>= 60 %), NO_RECOMENDADO (< 60 %)."""
import json,sys,datetime as dt
from pathlib import Path
from collections import Counter,defaultdict
D=Path(__file__).resolve().parents[1]/"docs/data_catalog"

def od(s):return dt.date.fromisoformat(s).toordinal()
def runs(dates,maxgap=4):
    out=[];cur=[]
    for d in sorted(dates):
        if cur and od(d)-od(cur[-1])>maxgap:out.append(cur);cur=[]
        cur.append(d)
    if cur:out.append(cur)
    return [(r[0],r[-1],len(r)) for r in out]

def main():
    cat=json.loads((D/"catalog.json").read_text());sess=json.loads((D/"sessions.json").read_text());I=cat["instruments"];cur={};reexp=defaultdict(list)
    for sym,v in I.items():
        conflict_contracts={k["contract"] for k in v["source_conflicts"] if k["days_common"] and k["days_rel_diff_gt_1pct"]/k["days_common"]>0.10}
        rows=sess[sym];reasons=Counter();appr=[];by_contract=defaultdict(list);excl=defaultdict(list);cave=[]
        for r in rows:
            if r["post_holdout"]:reasons["holdout"]+=1;excl["holdout"].append(r["date"]);continue
            if r["below_25pct_instrument_median"]:reasons["liquidez_baja"]+=1;excl["liquidez_baja"].append(r["date"]);continue
            if r["thin_minutes"]:reasons["sesion_truncada"]+=1;excl["sesion_truncada"].append(r["date"]);continue
            appr.append(r["date"]);by_contract[r["contract"]].append(r)
            if r["contract"] in conflict_contracts:cave.append(r["date"])
        n_el=len(rows)-reasons["holdout"];frac=len(appr)/max(1,n_el)
        verdict="APROBADO" if frac>=0.85 and not cave and not v["expected_contracts_missing"] else ("CON_SALVEDADES" if frac>=0.60 else "NO_RECOMENDADO")
        prim={}
        for c,rs in by_contract.items():
            cnt=Counter((r["dataset"],r["file"]) for r in rs);(ds,fl),n=cnt.most_common(1)[0];prim[c]={"dataset":ds,"file":fl,"approved_sessions":len(rs),"first":rs[0]["date"],"last":rs[-1]["date"],"other_sources":sorted({f"{r['dataset']}:{r['file']}" for r in rs}-{f"{ds}:{fl}"})}
        cur[sym]={"verdict":verdict,"tick_size":v["tick_size"],"tick_value_usd":v["tick_value_usd"],"eligible_sessions":len(rows),"approved_sessions":len(appr),"approved_fraction_of_eligible":round(frac,3),
                  "approved_ranges":[{"first":a,"last":b,"sessions":n} for a,b,n in runs(appr)],"excluded":{k:{"n":len(x),"dates_sample":x[:12]} for k,x in excl.items()},
                  "caveat_sessions_source_conflict":{"n":len(cave),"contracts":sorted(conflict_contracts)},"primary_source_by_contract":prim,"holdout_sessions_present":reasons["holdout"],
                  "last_approved_session":appr[-1] if appr else None}
        # --- necesidades de re-exportación o re-subida
        if v["expected_contracts_missing"]:reexp[sym].append(("CONTRATO_FALTANTE",f"Exportar {', '.join(v['expected_contracts_missing'])} (contratos del ciclo estándar que debieron ser líder y no están)."))
        if v["missing_weekdays"]["unexplained"]:reexp[sym].append(("SESIONES_FALTANTES","Faltan sesiones que no son feriados: "+", ".join(v["missing_weekdays"]["unexplained"])+". Reexportar esos días."))
        if conflict_contracts:reexp[sym].append(("FUENTES_EN_CONFLICTO","Contratos con fuentes que difieren de forma material: "+", ".join(sorted(conflict_contracts))+". Reexportar de NinjaTrader y comparar contra las dos."))
        if v["last_date"]<"2026-09-25":reexp[sym].append(("COBERTURA_CORTA",f"Los datos terminan el {v['last_date']}; para julio-septiembre de 2026 hace falta exportar desde {v['last_date']}."))
        if frac<0.60:reexp[sym].append(("ILIQUIDO_NO_SE_ARREGLA",f"Solo {len(appr)} de {len(rows)} sesiones elegibles pasan la liquidez; no es un problema de exportación: el instrumento es poco líquido. No usar como serie continua."))
    ds_cnt=defaultdict(lambda:{"sessions":0,"instruments":set()})
    for sym,rows in sess.items():
        ok={r["date"] for r in rows if not(r["post_holdout"] or r["below_25pct_instrument_median"] or r["thin_minutes"])}
        for r in rows:
            if r["date"] in ok:ds_cnt[r["dataset"]]["sessions"]+=1;ds_cnt[r["dataset"]]["instruments"].add(sym)
    roles=[]
    for d in cat["datasets"]:
        n=ds_cnt.get(d["slug"],{"sessions":0,"instruments":set()});kind=d["kind"];slug=d["slug"]
        if kind=="ticks" and n["sessions"]>0:role="PRIMARIO (aporta sesiones aprobadas)"
        elif kind=="ticks" and "dukascopy" in slug:role="SPOT (no es futuro): ver la sección de Dukascopy"
        elif kind=="ticks":role="REDUNDANTE o sin sesiones aprobadas (no usar como fuente; conservar como respaldo)"
        elif "code" in slug:role="CÓDIGO del proyecto"
        elif "discovery-cache" in slug or "data-catalog" in slug:role="DERIVADO (caché / inventario)"
        else:role="ARTEFACTOS / EVIDENCIA (no son datos de mercado)"
        roles.append({"slug":slug,"role":role,"approved_sessions_supplied":n["sessions"],"instruments":sorted(n["instruments"]),"private":d["private"],"mb":round((d["bytes"] or 0)/1e6),"note":"PÚBLICO: pasarlo a privado" if not d["private"] else ""})
    # ---- salidas
    (D/"curated.json").write_text(json.dumps({"generated_utc":cat["generated_utc"],"rules":__doc__,"holdout_first_trade_date":cat["holdout_first_trade_date"],"dataset_roles":roles,"instruments":cur,"spot_series":cat.get("spot_series",{})},indent=1))
    L=["# Datos aprobados para análisis (generado)","","Reglas fijas en `tools/data_curate.py` (iguales para todos). **Usar solo lo que figura acá como aprobado.** Fuente: `curated.json`.","",
       "## Resumen","","| Instrumento | Veredicto | Sesiones elegibles | Aprobadas | Última sesión aprobada | Rangos aprobados (primero..último, sesiones) |","|---|---|---:|---:|---|---|"]
    for s,x in cur.items():L.append(f"| {s} | **{x['verdict']}** | {x['eligible_sessions']} | {x['approved_sessions']} ({x['approved_fraction_of_eligible']:.0%}) | {x['last_approved_session']} | "+"; ".join(f"{r['first']}..{r['last']} ({r['sessions']})" for r in x["approved_ranges"][:6])+(" …" if len(x["approved_ranges"])>6 else "")+" |")
    L+=["","## Fuente primaria por contrato (la que aporta más sesiones aprobadas)",""]
    for s,x in cur.items():
        L+=["",f"### {s}","","| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |","|---|---|---|---:|---|---|"]
        for c,p in x["primary_source_by_contract"].items():L.append(f"| {c} | `{p['dataset']}` | `{p['file']}` | {p['approved_sessions']} | {p['first']}..{p['last']} | {'<br>'.join(f'`{o}`' for o in p['other_sources']) or '-'} |")
        ex=", ".join(f"{k}: {y['n']}" for k,y in x["excluded"].items());L.append("");L.append(f"Excluidas: {ex or 'ninguna'}. Sesiones con salvedad por fuentes en conflicto: {x['caveat_sessions_source_conflict']['n']}.")
    L+=["","## Rol de cada dataset de Kaggle","","| Dataset | Rol | Sesiones aprobadas que aporta | Instrumentos | Privado | MB | Nota |","|---|---|---:|---|---|---:|---|"]+[f"| `{r['slug']}` | {r['role']} | {r['approved_sessions_supplied']} | {', '.join(r['instruments']) or '-'} | {'sí' if r['private'] else '**NO**'} | {r['mb']:,} | {r['note']} |" for r in roles]
    (D/"CURATED.md").write_text("\n".join(L)+"\n")
    R=["# Qué hay que re-exportar o re-subir (generado)","","Cada punto sale de una regla verificable sobre el catálogo. Orden de prioridad: contratos faltantes y fuentes en conflicto primero.","",]
    for kind in ("CONTRATO_FALTANTE","FUENTES_EN_CONFLICTO","SESIONES_FALTANTES","COBERTURA_CORTA","ILIQUIDO_NO_SE_ARREGLA"):
        items=[(s,t) for s,l in reexp.items() for k,t in l if k==kind]
        if items:R+=[f"## {kind}",""]+[f"- **{s}:** {t}" for s,t in items]+[""]
    st=cat.get("stub_files",[])
    if st:R+=["## ARCHIVOS_VACIOS_O_DE_RELLENO","","Archivos con menos de 1.000 trades (casi vacíos): no se usan y el contrato **debe reexportarse**.","","| Dataset | Archivo | Contrato | Trades | Tamaño (bytes) |","|---|---|---|---:|---:|"]+[f"| `{x['dataset']}` | `{x['file']}` | {x['contract']} | {x['trades']} | {x['bytes']:,} |" for x in st]+[""]
    sp=cat.get("spot_series",{}).get("XAUUSD")
    if sp and sp.get("layout")=="unified_file":
        t=sp["ticks"];R+=["## DUKASCOPY XAU/USD (spot)","",f"- Dataset unificado vigente: {t['first_date']}..{t['last_date']}, {t['sessions']} sesiones; días hábiles sin datos sin explicación: {', '.join(t['weekdays_without_data_unexplained']) or 'ninguno'}. **No requiere re-subida.**",""]
    elif sp:R+=["## DUKASCOPY XAU/USD (spot)","",f"- Meses faltantes dentro del rango ya subido: {', '.join(sp['missing_months_in_range'])}.",""]
    (D/"REEXPORT.md").write_text("\n".join(R)+"\n");print(json.dumps({s:(x["verdict"],x["approved_sessions"],x["eligible_sessions"]) for s,x in cur.items()}));print("reexport items",sum(len(l) for l in reexp.values()))
if __name__=="__main__":main()
