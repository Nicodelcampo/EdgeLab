#!/usr/bin/env python3
r"""
Procesa, re-comprime a ZSTD-19 y sube a Kaggle el nuevo dataset canónico de ticks de NT8 (2025-2026Q3).

Instrumentos: MES, MNQ, MYM, RTY, YM
Procedencia: NinjaTrader 8 (Decisión Nico 28/09/2026, Auditoría 054)
Ventana: jul-2025 a apertura holdout A3 (1-oct-2026 00:00 UTC / 2026-09-30 17:00 CT)
Compresión: Parquet Zstandard nivel 19 (ZSTD:19)
Kaggle Dataset: nicolasbuttaro/edgelab-ticks-nt8-canonical
"""
import os
import sys
import json
import time
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import concurrent.futures

import pyarrow as pa
import pyarrow.parquet as pq
from kaggle.api.kaggle_api_extended import KaggleApi

REPO_ROOT = Path(r"E:\EdgeLab")
DATA_ROOT = REPO_ROOT / "data" / "nt8_2025_2026q3"
CATALOG_ROOT = REPO_ROOT / "docs" / "research" / "contract_regimes"
DOCS_ROOT = Path(r"E:\EdgeLab-unified-viewer\docs\research")
STAGING_DIR = Path(r"E:\kaggle_staging\edgelab-ticks-nt8-canonical")

DATASET_SLUG = "edgelab-ticks-nt8-canonical"
DATASET_REF = f"nicolasbuttaro/{DATASET_SLUG}"
DATASET_TITLE = "EdgeLab Ticks NT8 Canonical (2025-2026Q3)"
HOLDOUT_A3_MAX_NS = 1_790_805_600 * 1_000_000_000  # 2026-09-30 17:00 CT

INSTRUMENTS = ["MES", "MNQ", "MYM", "RTY", "YM"]


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(16 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def process_parquet_file(args):
    src_file, dst_file, inst, contract = args
    t0 = time.time()
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    
    pf_src = pq.ParquetFile(src_file)
    schema = pf_src.schema_arrow
    src_rows = pf_src.metadata.num_rows
    src_size = src_file.stat().st_size
    
    # Read and stream batches to ZSTD:19 writer
    writer = pq.ParquetWriter(dst_file, schema, compression="zstd", compression_level=19)
    
    min_ts = None
    max_ts = None
    rows_written = 0
    
    for batch in pf_src.iter_batches(batch_size=500_000):
        # Holdout and timestamp check
        ts_col = batch.column("ts_utc_ns").to_numpy()
        b_min = int(ts_col.min()) if len(ts_col) else None
        b_max = int(ts_col.max()) if len(ts_col) else None
        if b_min is not None:
            min_ts = b_min if min_ts is None else min(min_ts, b_min)
            max_ts = b_max if max_ts is None else max(max_ts, b_max)
        
        post_holdout = int((ts_col >= HOLDOUT_A3_MAX_NS).sum())
        assert post_holdout == 0, f"HOLDOUT VIOLATION in {src_file.name}: {post_holdout} rows >= {HOLDOUT_A3_MAX_NS}"
        
        writer.write_batch(batch)
        rows_written += len(batch)
        
    writer.close()
    
    dst_size = dst_file.stat().st_size
    dst_sha = get_file_sha256(dst_file)
    
    # Verify metadata
    pf_dst = pq.ParquetFile(dst_file)
    assert pf_dst.metadata.num_rows == src_rows, f"Row count mismatch {src_file.name}: {pf_dst.metadata.num_rows} vs {src_rows}"
    assert pf_dst.schema_arrow == schema, f"Schema mismatch in {src_file.name}"
    
    elapsed = time.time() - t0
    ratio = (1.0 - (dst_size / src_size)) * 100.0 if src_size > 0 else 0.0
    
    print(f"[{inst}] {contract}: {src_rows:,} rows | {src_size/1e6:.1f}MB -> {dst_size/1e6:.1f}MB (-{ratio:.1f}%) in {elapsed:.1f}s", flush=True)
    
    return {
        "instrument": inst,
        "contract": contract,
        "filename": dst_file.name,
        "relative_path": f"{inst}/{dst_file.name}",
        "rows": src_rows,
        "size_orig_bytes": src_size,
        "size_zstd_bytes": dst_size,
        "compression_ratio": round(src_size / max(dst_size, 1), 2),
        "savings_pct": round(ratio, 1),
        "sha256": dst_sha,
        "min_ts_ns": min_ts,
        "max_ts_ns": max_ts,
        "elapsed_s": round(elapsed, 1)
    }


def stage_all(max_workers=4):
    print("=" * 70)
    print(f"Iniciando staging canónico NT8 en {STAGING_DIR}")
    print(f"Destino Kaggle: {DATASET_REF}")
    print(f"Compresión: Parquet Zstandard (nivel 19)")
    print("=" * 70)
    
    if STAGING_DIR.exists():
        print(f"Limpiando directorio de staging previo: {STAGING_DIR}")
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    
    tasks = []
    metadata_files = []
    
    for inst in INSTRUMENTS:
        inst_dir = DATA_ROOT / f"{inst}_parquet"
        assert inst_dir.exists(), f"Directorio no encontrado: {inst_dir}"
        
        # Parquets
        for pf in sorted(inst_dir.glob("*.parquet")):
            parts = pf.stem.split("_")
            cont = f"{inst} {parts[1]}" if len(parts) > 1 else inst
            dst_f = STAGING_DIR / inst / pf.name
            tasks.append((pf, dst_f, inst, cont))
            
        # Manifests and session summaries
        for jf in sorted(inst_dir.glob("*.json")):
            dst_j = STAGING_DIR / inst / jf.name
            dst_j.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(jf, dst_j)
            metadata_files.append((dst_j, f"{inst}/{jf.name}"))

    # Catalogs
    cat_dst_dir = STAGING_DIR / "catalogs"
    cat_dst_dir.mkdir(parents=True, exist_ok=True)
    for inst in INSTRUMENTS:
        cat_file = CATALOG_ROOT / f"{inst}_nt8_2025_2026q3_sessions_catalog.json"
        if cat_file.exists():
            dst_c = cat_dst_dir / cat_file.name
            shutil.copyfile(cat_file, dst_c)
            metadata_files.append((dst_c, f"catalogs/{cat_file.name}"))
        else:
            print(f"Advertencia: no se encontró catálogo para {inst} en {cat_file}")
            
    # Docs provenance
    docs_dst_dir = STAGING_DIR / "docs"
    docs_dst_dir.mkdir(parents=True, exist_ok=True)
    for doc_name in ["DECISION_PROVEEDOR_CANONICO_NT8_20260928.md", "PARIDAD_PROVEEDOR_LUCID_NT8_20260928.md"]:
        doc_src = DOCS_ROOT / doc_name
        if doc_src.exists():
            dst_d = docs_dst_dir / doc_name
            shutil.copyfile(doc_src, dst_d)
            metadata_files.append((dst_d, f"docs/{doc_name}"))

    print(f"\nProcesando {len(tasks)} archivos Parquet con {max_workers} workers...")
    t0_total = time.time()
    results = []
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_parquet_file, t): t for t in tasks}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)
            
    results.sort(key=lambda x: (x["instrument"], x["contract"]))
    t_elapsed = time.time() - t0_total
    
    total_rows = sum(r["rows"] for r in results)
    total_orig_mb = sum(r["size_orig_bytes"] for r in results) / 1e6
    total_zstd_mb = sum(r["size_zstd_bytes"] for r in results) / 1e6
    savings = (1.0 - (total_zstd_mb / total_orig_mb)) * 100.0
    
    print("\n" + "=" * 70)
    print(f"RECOMPRESIÓN COMPLETADA en {t_elapsed:.1f}s")
    print(f"Total filas: {total_rows:,}")
    print(f"Tamaño original (Snappy): {total_orig_mb:,.1f} MB ({total_orig_mb/1024:.2f} GB)")
    print(f"Tamaño comprimido (ZSTD-19): {total_zstd_mb:,.1f} MB ({total_zstd_mb/1024:.2f} GB)")
    print(f"Ahorro total de espacio: {savings:.1f}%")
    print("=" * 70)
    
    # Calculate SHA256 for metadata files
    all_files_sha = []
    for r in results:
        all_files_sha.append((r["relative_path"], r["sha256"]))
        
    for dst_f, rel_path in metadata_files:
        sha = get_file_sha256(dst_f)
        all_files_sha.append((rel_path, sha))
        
    # Write dataset-metadata.json
    metadata = {
        "title": DATASET_TITLE,
        "id": DATASET_REF,
        "licenses": [{"name": "other"}],
        "isPrivate": True,
        "subtitle": "Canonical NT8 ticks (MES, MNQ, MYM, RTY, YM) 2025-2026Q3 ZSTD-19"
    }
    with open(STAGING_DIR / "dataset-metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    all_files_sha.append(("dataset-metadata.json", get_file_sha256(STAGING_DIR / "dataset-metadata.json")))

    # Generate README.md
    readme_content = generate_readme(results, total_rows, total_orig_mb, total_zstd_mb, savings)
    with open(STAGING_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    all_files_sha.append(("README.md", get_file_sha256(STAGING_DIR / "README.md")))

    # Generate AUDIT_MANIFEST.json
    audit_manifest = {
        "schema_version": "canonical_nt8_dataset_v1",
        "dataset_ref": DATASET_REF,
        "title": DATASET_TITLE,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "NinjaTrader 8 (NT8)",
        "source_decision": "DECISION_PROVEEDOR_CANONICO_NT8_20260928.md",
        "holdout_amendment": "HOLDOUT-A3 (2026-09-28)",
        "holdout_max_timestamp_ns": HOLDOUT_A3_MAX_NS,
        "compression": "zstd:19",
        "summary": {
            "instruments": INSTRUMENTS,
            "total_contracts": len(results),
            "total_rows": total_rows,
            "size_snappy_mb": round(total_orig_mb, 2),
            "size_zstd_mb": round(total_zstd_mb, 2),
            "savings_percent": round(savings, 2)
        },
        "files": results
    }
    with open(STAGING_DIR / "AUDIT_MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(audit_manifest, f, indent=2)
    all_files_sha.append(("AUDIT_MANIFEST.json", get_file_sha256(STAGING_DIR / "AUDIT_MANIFEST.json")))

    # Write files.sha256
    all_files_sha.sort(key=lambda x: x[0])
    with open(STAGING_DIR / "files.sha256", "w", encoding="utf-8") as f:
        for rel_p, sha in all_files_sha:
            f.write(f"{sha}  {rel_p}\n")

    return results, total_zstd_mb


def generate_readme(results, total_rows, total_orig_mb, total_zstd_mb, savings):
    lines = [
        f"# {DATASET_TITLE}",
        "",
        "## 1. Contexto y Procedencia Canónica",
        "",
        "Por decisión canónica de arquitectura de datos (28/09/2026, Nico; Auditoría 054):",
        "- **NinjaTrader 8 (NT8)** se establece como el **proveedor canónico prospectivo** de datos de ticks y L2 para EdgeLab.",
        "- Este dataset reemplaza la dependencia histórica de feeds de terceros (Lucid) para los instrumentos activos de investigación.",
        "- **Gobernanza estricta:** Los datos medidos sobre Lucid en el pasado permanecen etiquetados como Lucid y no se sobrescriben ni concatenan directamente sin auditoría de proveedor.",
        "- **Límite de Holdout:** Cumple estrictamente con la enmienda `HOLDOUT-A3` (descubrimiento y réplica prospectiva cerrados antes de la apertura del holdout A3: `1790805600000000000` = 2026-09-30 17:00 CT).",
        "",
        "## 2. Formato y Compresión Máxima",
        "",
        "- **Formato Analítico:** Apache Parquet (`canonical_tick_v1`).",
        "- **Compresión:** **Zstandard Nivel 19 (`zstd:19`)**.",
        f"- **Ratio de Reducción:** De **{total_orig_mb/1024:.2f} GB** (Snappy estándar) a **{total_zstd_mb/1024:.2f} GB** (**-{savings:.1f}%** de reducción).",
        "- **Compatibilidad:** Lectura nativa, directa y sin descompresión previa en DuckDB, Polars, PyArrow y Pandas en notebooks de Kaggle.",
        "",
        "## 3. Esquema de Datos (`canonical_tick_v1`)",
        "",
        "| Campo | Tipo | Descripción |",
        "| :--- | :--- | :--- |",
        "| `ts_utc_ns` | int64 | Timestamp en nanosegundos UTC |",
        "| `ts_local_ns` | int64 | Timestamp local registrado (duplica ts_utc_ns según P-28) |",
        "| `sequence` | int64 | Índice monotónico estricto de evento dentro del contrato |",
        "| `price_ticks` | int64 | Precio entero en múltiplos de `tick_size` (evita floating point drift) |",
        "| `bid_ticks` | int64 | Best Bid vigente en ticks |",
        "| `ask_ticks` | int64 | Best Ask vigente en ticks |",
        "| `volume` | int32 | Volumen del trade |",
        "| `aggressor` | string | Clasificación del trade (`buy`, `sell`, `unclassified`) |",
        "| `tick_type` | string | Tipo de tick (`trade`) |",
        "| `instrument` | string | Código del instrumento (`MES`, `MNQ`, `MYM`, `RTY`, `YM`) |",
        "| `contract` | string | Vencimiento (`MES 03-26`, etc.) |",
        "| `source_file` | string | Archivo original de procedencia del AddOn NT8 |",
        "| `source_row` | int64 | Fila de origen para trazabilidad e integridad de secuencia |",
        "",
        "## 4. Desglose de Contratos por Instrumento",
        "",
        "| Instrumento | Contrato | Filas | Tamaño ZSTD (MB) | Reducción (%) | SHA-256 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    
    for r in results:
        lines.append(f"| **{r['instrument']}** | `{r['contract']}` | {r['rows']:,} | {r['size_zstd_bytes']/1e6:.1f} MB | {r['savings_pct']:.1f}% | `{r['sha256'][:16]}...` |")
        
    lines.extend([
        "",
        f"**TOTAL:** **{len(results)} contratos**, **{total_rows:,} filas**, **{total_zstd_mb/1024:.2f} GB**.",
        "",
        "## 5. Catálogos y Manifiestos de Sesión",
        "",
        "En la carpeta `catalogs/` se incluyen los catálogos canónicos de sesiones completas e ilíquidas generados bajo la regla del roll por volumen:",
        "- `MES_nt8_2025_2026q3_sessions_catalog.json`",
        "- `MNQ_nt8_2025_2026q3_sessions_catalog.json`",
        "- `MYM_nt8_2025_2026q3_sessions_catalog.json`",
        "- `RTY_nt8_2025_2026q3_sessions_catalog.json`",
        "- `YM_nt8_2025_2026q3_sessions_catalog.json`",
        "",
        "## 6. Ejemplo de Uso en Kaggle (DuckDB / Polars)",
        "",
        "```python",
        "import duckdb",
        "",
        "# Consulta directa ultra-rápida sin descomprimir",
        "con = duckdb.connect()",
        "df = con.execute('''",
        "    SELECT instrument, contract, count(*) as n_ticks, min(ts_utc_ns), max(ts_utc_ns)",
        "    FROM '/kaggle/input/edgelab-ticks-nt8-canonical/*/*.parquet'",
        "    GROUP BY instrument, contract",
        "    ORDER BY instrument, contract",
        "''').df()",
        "print(df)",
        "```",
        ""
    ])
    
    return "\n".join(lines)


def upload_dataset():
    temp_dir = Path(r"E:\kaggle_staging\temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(temp_dir)
    os.environ["TMP"] = str(temp_dir)
    
    api = KaggleApi()
    api.authenticate()
    
    print("\n" + "=" * 70)
    print(f"VERIFICANDO ESTADO REMOTO EN KAGGLE: {DATASET_REF}")
    print("=" * 70)
    
    exists = False
    try:
        status = str(api.dataset_status(DATASET_REF))
        print(f"El dataset {DATASET_REF} ya existe en Kaggle. Estado actual: {status}")
        exists = True
    except Exception as e:
        print(f"El dataset {DATASET_REF} no existe todavía (o es nuevo): {e}")
        exists = False
        
    t0_up = time.time()
    
    if not exists:
        print(f"\nCreando nuevo dataset privado: {DATASET_REF}...")
        res = api.dataset_create_new(
            folder=str(STAGING_DIR),
            public=False,
            quiet=False,
            convert_to_csv=False,
            dir_mode="zip"
        )
        print("Respuesta de creación:", res)
    else:
        print(f"\nSubiendo nueva versión de {DATASET_REF}...")
        res = api.dataset_create_version(
            folder=str(STAGING_DIR),
            version_notes=f"Canonical NT8 2025-2026Q3 migration (ZSTD-19) {datetime.now(timezone.utc).isoformat()}",
            quiet=False,
            convert_to_csv=False,
            dir_mode="zip"
        )
        print("Respuesta de versión:", res)
        
    print(f"\nSubida completada en {time.time() - t0_up:.1f}s.")
    print("Esperando confirmación y procesamiento por parte de Kaggle CDN...")
    
    max_wait = 900
    t_start = time.time()
    while time.time() - t_start < max_wait:
        try:
            current_status = str(api.dataset_status(DATASET_REF))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Estado de {DATASET_REF}: {current_status}")
            if current_status.lower() == "ready":
                print("\n¡DATASET PROCESADO EXITOSAMENTE Y LISTO EN KAGGLE!")
                break
            if "error" in current_status.lower() or "fail" in current_status.lower():
                raise RuntimeError(f"Error en procesamiento de Kaggle: {current_status}")
        except Exception as e:
            print(f"Error consultando estado: {e}")
        time.sleep(15)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4, help="Número de workers concurrentes")
    parser.add_argument("--skip-staging", action="store_true", help="Saltear staging si ya existe")
    parser.add_argument("--skip-upload", action="store_true", help="Solo generar staging sin subir a Kaggle")
    args = parser.parse_args()
    
    if not args.skip_staging:
        stage_all(max_workers=args.workers)
    else:
        print(f"Usando staging existente en {STAGING_DIR}")
        
    if not args.skip_upload:
        upload_dataset()
    else:
        print("Subida salteada (--skip-upload)")


if __name__ == "__main__":
    main()
