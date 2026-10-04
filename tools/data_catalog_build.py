#!/usr/bin/env python3
"""Construye el catálogo legible (docs/data_catalog) desde el inventario crudo.
  python tools/data_inventory.py --out /data/catalog && python tools/data_catalog_build.py --scan-root /data/catalog --out docs/data_catalog"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.catalog.build import build,iso

def mb(b):return f"{(b or 0)/1e6:,.0f} MB"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--scan-root",required=True);ap.add_argument("--out",required=True);a=ap.parse_args();cat=build(Path(a.scan_root));o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
    (o/"catalog.json").write_text(json.dumps(cat,indent=1,default=float))
    I=cat["instruments"];L=["# Catálogo de instrumentos (generado)","",f"Generado {cat['generated_utc']}. Fuente de verdad: `catalog.json`. Holdout formal: sesiones de trading desde **{cat['holdout_first_trade_date']}** (HOLDOUT-A1): no leer.","",
        "## Índice rápido","","| Instrumento | Tick (USD/tick) | Rango | Sesiones con datos | Sesiones elegibles (líder, liquidez) | Contratos | Datos posteriores al 2026-06-30 | Días hábiles sin explicar | Contratos del ciclo que faltan | Sesiones líder < 25 % del volumen mediano |","|---|---|---|---:|---:|---:|---|---:|---|---:|"]
    for s,v in I.items():
        L.append(f"| {s} | {v['tick_size']} ({v['tick_value_usd']}) | {v['first_date']} a {v['last_date']} | {v['sessions_with_data']} | {v['eligible_sessions']} | {len(v['contracts'])} | {'sí' if v['data_after_2026-06-30_present'] else 'no'} | {len(v['missing_weekdays']['unexplained'])} rangos | {', '.join(v['expected_contracts_missing']) or '-'} | {v['leader_sessions_below_25pct_of_instrument_median']['n']} |")
    for s,v in I.items():
        L+=["",f"## {s}","",f"Tick {v['tick_size']} = USD {v['tick_value_usd']} por contrato. Sesiones con datos {v['sessions_with_data']}; elegibles {v['eligible_sessions']}; sesiones desde el holdout formal: {v['post_holdout_sessions']}.","",
            "### Contratos y fuentes","","| Contrato | Rango | Sesiones | Trades | Fuente(s): dataset / archivo (libro, agresor) |","|---|---|---:|---:|---|"]
        for c,x in v["contracts"].items():
            src="<br>".join(f"`{q['dataset']}` / `{q['file']}` ({q['first']}..{q['last']}, {q['sessions']} ses.; libro={'sí' if q['has_book'] else 'no'}, agresor={'sí' if q['has_aggressor'] else 'no'})" for q in x["sources"])
            L.append(f"| {c} | {x['first']} a {x['last']} | {x['sessions']} | {x['trades']:,} | {src} |")
        L+=["","### Serie líder (mayor volumen de la sesión anterior; sin retroceso) y rolls","","| Contrato líder | Desde | Hasta |","|---|---|---|"]+[f"| {q['contract']} | {q['first']} | {q['last']} |" for q in v["leader_segments"]]
        if v["rolls"]:
            L+=["","| Roll | Primera sesión del nuevo líder | Volumen previo viejo → nuevo | Razón |","|---|---|---|---:|"]+[f"| {r['from']} → {r['to']} | {r['first_session_as_leader']} | {r.get('volume_old','n/d')} → {r.get('volume_new','n/d')} | {r.get('ratio_new_over_old','n/d')} |" for r in v["rolls"]]
        L+=["",f"### Liquidez y calendario","",f"- **Contratos del ciclo estándar que faltan en los datos (y debieron ser líder en algún momento del rango):** {', '.join(v['expected_contracts_missing']) or 'ninguno'}.",
            f"- Volumen diario mediano del líder en este instrumento: {v['leader_median_daily_volume']:,.0f}. **Sesiones del líder por debajo del 25 % de esa mediana** (liquidez baja respecto del resto del instrumento, aunque pasen el filtro relativo): {v['leader_sessions_below_25pct_of_instrument_median']['n']}; rangos: {', '.join(v['leader_sessions_below_25pct_of_instrument_median']['ranges'][:15]) or 'ninguna'}.",f"- Sesiones no elegibles por volumen bajo (< 50 % de la mediana del contrato como líder): {v['ineligible_low_volume']['n']}. Rangos: {', '.join(v['ineligible_low_volume']['ranges'][:15]) or 'ninguna'}{' …' if len(v['ineligible_low_volume']['ranges'])>15 else ''}.",
            f"- Días hábiles sin datos por feriado de EE.UU. o Viernes Santo: {', '.join(v['missing_weekdays']['holidays']) or 'ninguno'}.",f"- **Días hábiles sin datos y sin explicación:** {', '.join(v['missing_weekdays']['unexplained']) or 'ninguno'}.",
            f"- Sesiones del líder con menos de la mitad de los minutos típicos (cierres tempranos o truncadas): {', '.join(v['thin_leader_sessions(<50%_of_median_minutes)']) or 'ninguna'}."]
        if v["gaps_inside_contract_life(>5_days)"]:L.append("- Huecos de más de 5 días dentro de la vida de un contrato (rebanadas parciales): "+"; ".join(f"{g['contract']}: {', '.join(g['gaps'])}" for g in v["gaps_inside_contract_life(>5_days)"])+".")
        if v["source_conflicts"]:
            L+=["","### Contratos con más de una fuente (comparación día a día de trades)","","| Contrato | A | B | Días A / B / comunes | Idénticos | Distintos (A más / B más) | Mediana A/B en días distintos | Dif. máx. relativa | Solo en A | Solo en B |","|---|---|---|---|---:|---|---|---:|---|---|"]
            L+=[f"| {c['contract']} | `{c['a']}` | `{c['b']}` | {c['days_a']} / {c['days_b']} / {c['days_common']} | {c['days_identical_trades']} | {c['days_different']} ({c['days_a_more_trades']} / {c['days_b_more_trades']}); > 1 %: {c['days_rel_diff_gt_1pct']} | {c['median_ratio_a_over_b_on_differing_days'] if c['median_ratio_a_over_b_on_differing_days'] is not None else '-'} | {c['max_rel_diff']} | {', '.join(c['only_in_a']) or '-'} | {', '.join(c['only_in_b']) or '-'} |" for c in v["source_conflicts"]]
    SP=cat.get("spot_series",{})
    if SP:
        L+=["","# Series spot (cotizaciones, no futuros)","","Ticks de cotización bid/ask de Dukascopy: **no son operaciones ejecutadas** y no tienen volumen real ni agresor; sirven para estrategias que dependen solo del precio (ver `edgelab/equivalence`). Costos y ejecución se modelan con el instrumento real."]
        for sym,v in SP.items():
            L+=["",f"## {sym} (spot, UTC)","",f"- Meses de ticks: {', '.join(v['ticks_months'])}.",f"- Meses de M1: {', '.join(v['m1_months'])}.",f"- **Meses faltantes dentro del rango:** {', '.join(v['missing_months_in_range']) or 'ninguno'}.",
                f"- Sesiones desde el holdout formal: {v['post_holdout_sessions']}.","","| Mes | Ticks: archivo | Filas | Sesiones | Rango | Precio mín–máx |","|---|---|---:|---:|---|---|"]
            for ym,x in sorted(v["files"]["ticks"].items()):L.append(f"| {ym} | `{x['file']}` | {x['rows']:,} | {x['sessions']} | {x['first_date']}..{x['last_date']} | {x['price_min']:.1f}–{x['price_max']:.1f} |")
    (o/"INSTRUMENTS.md").write_text("\n".join(L)+"\n")
    D=["# Datasets de Kaggle (generado)","","| Dataset | Tipo | Tamaño | Privado | Archivos | Actualizado |","|---|---|---:|---|---:|---|"]
    for d in cat["datasets"]:D.append(f"| `{d['slug']}` | {d['kind']} | {mb(d['bytes'])} | {'sí' if d['private'] else '**PÚBLICO**'} | {d['n_files']} | {(d['last_updated'] or '')[:10]} |")
    for d in cat["datasets"]:
        D+=["",f"## `{d['slug']}`","",f"Tipo: {d['kind']}. {mb(d['bytes'])}. {d['n_files']} archivos."]
        if d["tick_files"]:D.append("Archivos de ticks: "+", ".join(f"`{f}`" for f in d["tick_files"]))
        if d["unrecognized_parquet"]:D.append("Parquet con esquema no reconocido: "+"; ".join(f"`{u['file']}` columnas {u['columns']}" for u in d["unrecognized_parquet"]))
        if d["top_level_files"] and not d["tick_files"]:D.append("Archivos (primeros): "+", ".join(f"`{f}`" for f in d["top_level_files"][:15]))
        if d["readme_excerpt"]:D+=["","README del dataset (extracto):","","```",d["readme_excerpt"][:900],"```"]
    (o/"DATASETS.md").write_text("\n".join(D)+"\n")
    TF=["# Archivos de ticks (generado)","","| Dataset | Archivo | Contrato | Rango de sesiones | Sesiones | Trades | Libro | Agresor | Sesiones desde holdout | Desorden / libro cruzado / libro ≤ 0 |","|---|---|---|---|---:|---:|---|---|---:|---|"]
    for f in cat["tick_files"]:TF.append(f"| `{f['dataset']}` | `{f['file']}` | {f['contract']} | {f['first_trade_date']} a {f['last_trade_date']} | {f['sessions']} | {f['trades']:,} | {'sí' if f['has_book'] else 'no'} | {'sí' if f['has_aggressor'] else 'no'} | {f['post_holdout_sessions']} | {f['unsorted_events']} / {f['crossed_book']} / {f['no_book_le_0']} |")
    (o/"TICK_FILES.md").write_text("\n".join(TF)+"\n");print("catálogo escrito en",o,"| instrumentos",len(I),"| archivos de ticks",len(cat["tick_files"]))
if __name__=="__main__":main()
