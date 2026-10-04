#!/usr/bin/env python3
"""Convierte los JSON de auditoría (artifacts/discovery/audit/audit_*.json) en tablas Markdown. Descriptivo: no excluye nada."""
import argparse,collections,glob,json,re,sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--audit-dir",required=True);ap.add_argument("--out",required=True);a=ap.parse_args();L=[]
    reps=[json.loads(Path(f).read_text()) for f in sorted(glob.glob(f"{a.audit_dir}/audit_*.json"))]
    L+=["# Auditoría de datos: tablas generadas","","Generado por `tools/discovery_audit_report.py` desde `artifacts/discovery/audit/`. Descriptivo: no se excluyó ninguna sesión ni tick.","",
        "## Resumen por activo","","| Activo | Rango | Fechas con datos | Sesiones usadas (elegibles) | No elegibles por volumen | Días hábiles sin datos sin motivo conocido | Costo de libro entrada+salida p50 / p99 / máx (ticks) |","|---|---|---:|---:|---:|---:|---|"]
    for r in reps:
        al=r["asset_level"];fu=r["fills_used"]["entry_plus_exit_spread_ticks"]
        L.append(f"| {r['asset']} | {al['first_date']} a {al['last_date']} | {al['trade_dates_with_data']} | {al['eligible_sessions']} | {len(al['ineligible_low_volume'])} | {al['n_missing_without_known_reason']} | {fu['p50']:.0f} / {fu['p99']:.0f} / {fu['max']:.0f} |")
    for r in reps:
        al=r["asset_level"];L+=["",f"## {r['asset']}","","### Contratos (trades de la ventana previa al corte)","",
            "| Contrato | Trades | Libro cruzado | Libro bloqueado | Trade fuera del libro | Precio ≤ 0 | Vol. ≤ 0 | Sin agresor | Spread p50 / p99 / máx | Spread ≥ 100 ticks | Salto máx. en 60 s | Sesiones | Marcadas | Marcadas y usadas |","|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|"]
        for c,v in r["contracts"].items():
            t=v["tick_level"];s=v["session_level"];f=t["file"];sp=t["spread_ticks"];w=t.get("wide_spread_ge_100",{}).get("n",0)
            L.append(f"| {c} | {t['trades']:,} | {t['crossed_book']} | {t['locked_book']} | {t['trade_outside_book']} | {t['price_le_0']} | {t['volume_le_0']} | {f['aggressor'].get('unclassified',0)} | {sp['p50']:.0f} / {sp['p99']:.0f} / {sp['max']:.0f} | {w} | {t['jumps_within_60s_ticks']['max']:.0f} | {s['sessions']} | {s['n_flagged']} | {s.get('n_flagged_used_in_scan','-')} |")
        wid=[(c,v["tick_level"]["wide_spread_ge_100"]) for c,v in r["contracts"].items() if "wide_spread_ge_100" in v["tick_level"]]
        if wid:
            L+=["","Spreads ≥ 100 ticks (valores más frecuentes y horas CT con más casos):",""]
            for c,w in wid:
                top=", ".join(f"{x['ticks']:.0f} ({x['n']})" for x in w["most_frequent_values"][:3]);hrs=sorted(w["by_hour_ct"].items(),key=lambda kv:-kv[1])[:3]
                L.append(f"- {c}: {w['n']} ticks; valores {top}; horas CT {', '.join(f'{h}h ({n})' for h,n in hrs)}")
        kinds=collections.Counter();usedk=collections.Counter()
        for c,v in r["contracts"].items():
            for x in v["session_level"]["flagged"]:
                for fl in x["flags"]:
                    k="hueco ≥ 5 min en 08:30-15:00 CT" if fl.startswith("hueco_") else fl
                    kinds[k]+=1;usedk[k]+=int(x.get("used_in_scan",False))
        L+=["","Banderas de sesión (todas las sesiones del contrato / solo las usadas en el barrido):",""]+[f"- {k}: {n} / {usedk[k]}" for k,n in kinds.most_common()]
        L+=["",f"Días hábiles sin datos: "+(", ".join(f"{m['date']} ({m['note']})" for m in al["missing_weekdays"]) or "ninguno"),"","Rolls (diferencia de precio del contrato nuevo menos el viejo en el último minuto en común, en ticks):",""]
        L+=[f"- {x['from']} → {x['to']} desde {x['first_date']}: volumen previo {x.get('volume_old',0):,.0f} → {x.get('volume_new',0):,.0f}; diferencia {x.get('price_gap_ticks_new_minus_old','n/d')}" for x in al["rolls"]]
    Path(a.out).write_text("\n".join(L)+"\n");print("escrito",a.out)
if __name__=="__main__":main()
