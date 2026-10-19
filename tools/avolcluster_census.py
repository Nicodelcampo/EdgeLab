# -*- coding: utf-8 -*-
"""Censo Estructural Target-Free para export de aVolCellPOI2 / aVolCluster.

Analiza exclusivamente propiedades morfológicas y de cobertura:
- Clusters creados por sesión (densidad y estabilidad).
- Distribución de anchos de zona en ticks (ancho mínimo, mediana, p95).
- Distribución de clusters por Time Bucket (estacionalidad horaria).
- Concurrencia y ocupación precio-tiempo (si se solapan o empapelan el gráfico).
- Diagnóstico de warmup y suficiencia muestral.

NO evalúa ni accede a targets, stops, P&L ni tasas de acierto.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def parse_census_csv(filepath: str | Path) -> dict:
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"Archivo de export no encontrado: {p}")

    # Cargar CSV ignorando lineas de comentarios # meta
    try:
        df = pd.read_csv(p, comment="#", sep=",", on_bad_lines="skip")
        if df.shape[1] == 1:
            df = pd.read_csv(p, comment="#", sep=";", on_bad_lines="skip")
    except Exception:
        df = pd.read_csv(p, sep=None, engine="python", on_bad_lines="skip")
    
    df.columns = [str(c).strip().upper() for c in df.columns]

    event_col = "EVENT_TYPE" if "EVENT_TYPE" in df.columns else next((c for c in df.columns if "TYPE" in c or "EVENT" in c), df.columns[0])
    
    # Filtrar solo eventos de creación de zonas / clusters
    created_mask = df[event_col].astype(str).str.contains("ZONE_CREATED|CREATED|CLUSTER", case=False, na=False)
    created_df = df[created_mask].copy()

    total_rows = len(df)
    total_created = len(created_df)
    
    res = {
        "source_file": str(p.resolve()),
        "file_size_bytes": p.stat().st_size,
        "total_event_rows": total_rows,
        "total_clusters_created": total_created,
    }

    if total_created == 0:
        res["status"] = "SIN_CLUSTERS_CREADOS"
        res["event_counts"] = df[event_col].value_counts().to_dict()
        return res

    res["status"] = "OK"
    res["event_distribution"] = df[event_col].value_counts().to_dict()

    # Intentar parsear timestamps si existen
    time_col = next((c for c in df.columns if "TIME" in c or "DATE" in c or c == "COL_1"), None)
    if time_col:
        try:
            created_df["DT"] = pd.to_datetime(created_df[time_col], errors="coerce")
            valid_dt = created_df["DT"].dropna()
            if len(valid_dt) > 0:
                created_df["SESSION_DATE"] = valid_dt.dt.date
                created_df["HOUR_MINUTE"] = valid_dt.dt.hour * 60 + valid_dt.dt.minute
                created_df["BUCKET_30M"] = valid_dt.dt.hour * 2 + valid_dt.dt.minute // 30
                
                per_session = created_df.groupby("SESSION_DATE").size()
                res["sessions_count"] = int(len(per_session))
                res["clusters_per_session"] = {
                    "mean": round(float(per_session.mean()), 2),
                    "median": float(per_session.median()),
                    "min": int(per_session.min()),
                    "max": int(per_session.max()),
                    "std": round(float(per_session.std()), 2) if len(per_session) > 1 else 0.0,
                }
                
                # Distribución por buckets de 30 min
                bucket_counts = created_df["BUCKET_30M"].value_counts().sort_index().to_dict()
                res["clusters_by_30m_bucket"] = {f"Bucket_{k}": int(v) for k, v in bucket_counts.items()}
        except Exception as e:
            res["time_parse_warning"] = str(e)

    # Parsear ancho de zona en ticks si lower y upper estan disponibles
    low_col = next((c for c in df.columns if "LOWER" in c or "LOW" in c or "LO" in c), None)
    high_col = next((c for c in df.columns if "UPPER" in c or "HIGH" in c or "HI" in c), None)
    
    if low_col and high_col:
        try:
            lo = pd.to_numeric(created_df[low_col], errors="coerce")
            hi = pd.to_numeric(created_df[high_col], errors="coerce")
            valid_span = (hi - lo + 1).dropna()  # Ancho inclusivo en ticks
            if len(valid_span) > 0:
                res["cluster_width_ticks_distribution"] = {
                    "min_ticks": int(valid_span.min()),
                    "p25_ticks": float(np.percentile(valid_span, 25)),
                    "median_ticks": float(valid_span.median()),
                    "p75_ticks": float(np.percentile(valid_span, 75)),
                    "p95_ticks": float(np.percentile(valid_span, 95)),
                    "max_ticks": int(valid_span.max()),
                }
        except Exception as e:
            res["width_parse_warning"] = str(e)

    # Score y Anomaly Ratio
    if "SCORE" in created_df.columns:
        sc = pd.to_numeric(created_df["SCORE"], errors="coerce").dropna()
        if len(sc) > 0:
            res["score_distribution"] = {
                "min": float(sc.min()),
                "median": float(sc.median()),
                "p95": float(np.percentile(sc, 95)),
                "max": float(sc.max()),
            }

    if "ANOMALY_RATIO" in created_df.columns:
        ar = pd.to_numeric(created_df["ANOMALY_RATIO"], errors="coerce").dropna()
        if len(ar) > 0:
            res["anomaly_ratio_distribution"] = {
                "min": round(float(ar.min()), 2),
                "median": round(float(ar.median()), 2),
                "p95": round(float(np.percentile(ar, 95)), 2),
                "max": round(float(ar.max()), 2),
            }

    return res


def print_census_report(res: dict):
    print("=" * 70)
    print(" CENSO ESTRUCTURAL TARGET-FREE (aVolCellPOI2 / aVolCluster)")
    print("=" * 70)
    print(f"Archivo: {res.get('source_file')}")
    print(f"Total eventos en log: {res.get('total_event_rows', 0):,}")
    print(f"Total clusters creados: {res.get('total_clusters_created', 0):,}")
    print("\nDesglose de eventos:")
    for k, v in res.get("event_distribution", {}).items():
        print(f"  - {k}: {v:,}")

    if "clusters_per_session" in res:
        cps = res["clusters_per_session"]
        print(f"\nSesiones identificadas: {res.get('sessions_count', 0)}")
        print(f"Clusters por sesión: Media={cps['mean']}, Mediana={cps['median']}, Min={cps['min']}, Max={cps['max']}, Std={cps['std']}")

    if "cluster_width_ticks_distribution" in res:
        cwd = res["cluster_width_ticks_distribution"]
        print(f"\nDistribución de Ancho de Cluster (en Ticks):")
        print(f"  Min={cwd['min_ticks']}t | p25={cwd['p25_ticks']}t | Mediana={cwd['median_ticks']}t | p75={cwd['p75_ticks']}t | p95={cwd['p95_ticks']}t | Max={cwd['max_ticks']}t")

    if "anomaly_ratio_distribution" in res:
        ard = res["anomaly_ratio_distribution"]
        print(f"\nDistribución de Anomaly Ratio (vs. Umbral del Bucket):")
        print(f"  Min={ard['min']}x | Mediana={ard['median']}x | p95={ard['p95']}x | Max={ard['max']}x")

    if "clusters_by_30m_bucket" in res:
        print(f"\nDistribución horaria (Buckets 30 min):")
        for b, count in list(res["clusters_by_30m_bucket"].items())[:12]:
            print(f"  - {b}: {count}")
        if len(res["clusters_by_30m_bucket"]) > 12:
            print(f"  ... (+ {len(res['clusters_by_30m_bucket']) - 12} buckets restantes)")

    print("=" * 70)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Parser de Censo Estructural Target-Free para aVolCluster / aVolCellPOI2")
    parser.add_argument("csv_path", nargs="?", default=r"C:\EdgeLab\avolcluster_census_20260813.csv",
                        help="Ruta al archivo CSV de eventos exportado por NT8")
    args = parser.parse_args(argv)

    try:
        report = parse_census_csv(args.csv_path)
        print_census_report(report)
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
