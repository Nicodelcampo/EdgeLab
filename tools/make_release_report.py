#!/usr/bin/env python3
"""Genera docs/infra/LIQUID_RELEASE_20261014.md y ISSUE_RESOLUTION_LOG_20261014.json desde los metadatos de la release.

Sólo agregados (sin precios ni ticks): es público-seguro para el repo.
Uso: python tools/make_release_report.py --release D:/.../release --census D:/.../census --kaggle-audit D:/.../kaggle_audit --out docs/infra
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

D = "RESOLVED_WITH_EVIDENCE"
LOG = [
    ("D01", "P0", "Timezone no acreditado", D, "Ajuste al calendario CME por grupo de fuentes y por trimestre: {tz_ok} de {tz_n} grupos calzan con UTC (violación ≈ 1e-6; ART violaría 4–12 %), con cambio de horario estable. Los 15 con anomalías son MBT (calendario propio) y el NQ nativo explicado en D02.",
     "Residual: no hay logs de NinjaTrader ni verificación contra el feed (conexión `Simulation`). Alcance de la evidencia = calendario, no feed."),
    ("D02", "P0", "NQ fuente en cuarentena", D, "Causa raíz: el export nativo `NQ 09-26` trae 15 bloques de ticks copiados fila a fila con +3 h exactas (2026-06-17 → 07-02), 532.441 ticks, 100 % dentro del horario sin mercado. El export por día no los tiene. La release descarta las copias; el parquet `nq-preholdout/6` queda en CUARENTENA etiquetado.",
     "Residual: por qué el export nativo copia el bloque (requiere logs del exportador)."),
    ("D03", "P0", "ES roll prematuro", D, "Los ticks de domingo previos a la apertura no forman sesión. ES permanece en 12-25 durante octubre 2025 y rolla 16-sep-25, 16-dic-25, 17-mar-26, 16-jun-26 y 15-sep-26.",
     "Residual: el calendario CME oficial sigue pendiente (D06)."),
    ("D04", "P0", "Máscara retrospectiva", D, "La decisión de cada sesión usa sólo D-1 y constantes congeladas; prueba de invariancia por mutación del futuro en `tests/data/test_liquid_release_selection.py`.",
     "Las constantes se calibraron descriptivamente sobre toda la muestra pre-holdout: son una PROPUESTA hasta que Nico las apruebe (D07)."),
    ("D05", "P0", "Completitud inventada / ausencia = 0", "OPEN", "Estados explícitos por sesión (incluida, sin contrato elegible, indeterminada, contrato elegido sin datos) y por día de calendario (OPEN/SHORT/CLOSED/MISSING_EXPORT). Nunca se emite 'cero verificado'.",
     "Falta la matriz rectangular contrato×sesión con evidencia de captura por contrato."),
    ("D06", "P0", "Calendario histórico revisado", "BLOCKED_UPSTREAM", "Calendario derivado de los datos (`calendar_derived.parquet`): feriados/cierres tempranos por volumen de todos los activos.",
     "Hace falta el calendario histórico oficial de CME (feriados, cierres cortos, DST)."),
    ("D07", "P0", "Liquidez relativa vs absoluta", "OPEN", "Límites absolutos por activo (volumen, ticks, spread típico) como política PROPUESTA en `liquidity_policy.json`.",
     "`approved_by = null`: requiere aprobación de Nico antes de cualquier uso de research."),
    ("D08", "P1", "Fuentes en conflicto", D, "Regla fija por (contrato, sesión): más minutos activos, menor hueco, luego export por día > nativo > parquet derivado. {conf} sesiones con diferencias de contenido registradas en `source_conflicts.parquet`; 97 % de las horas comparadas son idénticas (mediana de diferencia: 1 tick).",
     "No hay un tercer feed independiente para decidir cuál es 'verdad' cuando difieren por pocos ticks."),
    ("D09", "P1", "Contratos/fechas faltantes", "OPEN", "`metadata/MISSING_EXPORTS.md`: {p0} sesiones P0 y {p1} sesiones P1 con contrato y rango de fechas exactos.",
     "Exportar lo listado con el AddOn `EdgeLabTickHistory`; RTY y parte de MYM dependen de parquet derivado."),
    ("D10", "P1", "Esquemas heterogéneos", D, "Lectores explícitos por formato (texto NT8 y parquet canonical_tick_v1) con validación de grilla antes del redondeo; tick y valor por tick de 14 activos (incluye MGC, RTY y MBT, que faltaban en el contrato) verificados contra la grilla de los datos.",
     "Sin residual conocido."),
    ("D11", "P1", "Grilla/tick y procedencia de quote/agresor", D, "Grilla validada fila a fila antes de convertir (STOP si falla); quotes inválidos quedan `-1`; agresor por regla de quotes v1 y 0 si el libro está locked/cruzado/ausente.",
     "La procedencia upstream de bid/ask no se puede verificar sin logs."),
    ("D12", "P1", "Identidad local no prueba continuidad upstream", "BLOCKED_UPSTREAM", "Se conservan `source_id` (SHA-256 del origen) y `source_row`; no se deduplica por precio/tiempo/volumen iguales; `release_row` se declara distinta de la secuencia del exchange.",
     "Sin ID upstream no se puede probar continuidad."),
    ("D13", "P1", "Quotes locked y agresor desconocido", D, "Se conservan y se miden por sesión (columnas `locked`, `crossed`, `noquote` del escaneo).", "Política de uso por indicador pendiente."),
    ("D14", "P0", "Filtro después de lectura / holdout", D, "Nuevo lector: row groups por estadísticas de `trade_date`, STOP ante grupo mixto o sin estadísticas; constructor: corte del holdout sobre bytes antes de decodificar. Pruebas con lector espía.",
     "`continuous_contract.py` y los lectores legacy NO se tocaron (D18)."),
    ("D15", "P0", "Integridad/versiones débiles", D, "Nuevo lector exige manifiesto, tamaño y SHA-256 exactos; prueba de mismo tamaño con distinto contenido.", "El helper legacy `edgelab_data.py` no se modificó."),
    ("D16", "P0", "Rutas ambiguas", D, "Nuevo lector: rutas relativas exactas, sin traversal ni symlink, sin búsqueda por basename.", "Legacy sin cambios."),
    ("D17", "P1", "Cache no ligada al contenido", D, "`cache_key(sha, schema, transform, version)` en el lector nuevo.", "Las cachés legacy no se migraron."),
    ("D18", "P0", "Wiring protegido no global", "OPEN", "El lector nuevo es opt-in y está probado.", "Falta el mapa de call-sites y conectarlo en autónomo, notebooks y CLI."),
    ("D19", "P1", "Rolls, estado y lookbacks", D, "Contrato real por fila, `regime_id` por roll, sin back-adjust ni empalme; el consumidor debe reiniciar estado al cambiar `regime_id`.", "Los consumidores existentes no se auditaron."),
    ("D20", "P1", "Derivados pueden seguir viejos", "OPEN", "Los agregados v1 (1/30/60 s) y la caché de descubrimiento quedaron etiquetados como BLOQUEADOS/ARCHIVO en Kaggle.", "Regenerar barras desde la release y clasificar resultados históricos por dependencia."),
    ("D21", "P1", "Licencia/privacidad y spot/futuro", "OPEN", "Los {dsn} datasets de la cuenta están en privado; spot (Dukascopy) etiquetado `SPOT` y separado de CME.", "La decisión de licencia de redistribución sigue siendo de Nico."),
    ("D22", "P2", "Inventarios/pins desactualizados", D, "Inventario paginado completo ({dsn} datasets, {ker} kernels), mapa en `config/kaggle_space_map_20261014.json` y `KAGGLE_SPACE_INDEX.md`; la release se fija por SHA-256 en `release_manifest.json`.", "Sin residual."),
    ("D23", "P1", "Warmup, cobertura y claims", D, "La primera sesión de cada activo (sin D-1) y las sin contrato elegible se excluyen y listan; no se declara certificación ni edge.", "Warmup específico de cada indicador queda a cargo del consumidor."),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--kaggle-audit", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--commit", default="?")
    a = ap.parse_args()
    root, meta, cen = Path(a.release), Path(a.release) / "metadata", Path(a.census)
    man = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
    idx = pd.read_parquet(meta / "session_index.parquet")
    pol = json.loads((meta / "liquidity_policy.json").read_text(encoding="utf-8"))
    tz = pd.read_csv(cen / "tz_groups.csv")
    ex = pd.read_csv(meta / "missing_exports.csv")
    ver = json.loads((meta / "verification.json").read_text(encoding="utf-8")) if (meta / "verification.json").exists() else []
    conf = len(pd.read_parquet(meta / "source_conflicts.parquet")[["contract", "trade_date"]].drop_duplicates()) if (meta / "source_conflicts.parquet").exists() else 0
    kb = pd.read_csv(Path(a.kaggle_audit) / "kaggle_vs_sources_by_file.csv")
    tot = {c: int(kb[c].sum()) for c in ("EQUAL", "CLOSE", "DIFF", "KAGGLE_ONLY", "SOURCE_ONLY") if c in kb}
    fmt = dict(tz_ok=int((tz.verdict == "UTC_VERIFIED").sum()), tz_n=len(tz), conf=conf, p0=int(ex[ex.priority == "P0"].sessions.sum()),
               p1=int(ex[ex.priority == "P1"].sessions.sum()), dsn=41, ker=248)
    L = ["# Release líquida de ticks — informe del 2026-10-14", "",
         f"**Estado: `{man['status']}`.** Un Parquet por activo ({len(man['assets'])} activos), sólo sesiones con contrato líquido elegido causalmente, sin holdout.",
         "No es un certificado de datos ni autoriza research. La política de liquidez es una **propuesta sin aprobar**. Respuesta al handoff "
         "[`LOCAL_AGENT_LIQUID_DATA_REPAIR_HANDOFF_20261014.md`](LOCAL_AGENT_LIQUID_DATA_REPAIR_HANDOFF_20261014.md).", "",
         "Dónde está: dataset privado de Kaggle `nicolasbuttaro/edgelab-liquid-ticks-20261014` y copia local `D:\\edgelab_release_work\\release_20261014`. "
         f"Código: rama `data/liquid-release-20261014`, commit `{a.commit}`. Leer primero `README_AGENTES.md` dentro de la release.", "",
         "## 1. Contenido por activo", "",
         "| activo | filas | sesiones incluidas | rango | tamaño | sin contrato elegible | indeterminadas | contrato elegido sin datos |", "|---|---:|---:|---|---:|---:|---:|---:|"]
    tr = rows = 0
    for inst, info in man["assets"].items():
        d = idx[idx["instrument"] == inst]["status"].value_counts()
        L.append(f"| {inst} | {info['rows']:,} | {info['sessions']} | {info['first_trade_date']}→{info['last_trade_date']} | {info['bytes'] / 1e9:.2f} GB | "
                 f"{int(d.get('NO_ELIGIBLE', 0))} | {int(d.get('UNDETERMINED', 0))} | {int(d.get('EXCLUDED_SELECTED_CONTRACT_HAS_NO_DATA', 0))} |")
        tr += info["rows"]
    L += ["", f"Total: **{tr:,} filas**, {sum(v['bytes'] for v in man['assets'].values()) / 1e9:.1f} GB.", ""]
    if ver:
        L += ["## 2. Verificación independiente", "", "`tools/verify_release.py` relee cada archivo y compara con el censo: filas totales y por sesión (exacto), un solo contrato por sesión y el de la decisión, `regime_id` sin retrocesos, `ts` no decreciente, sin holdout, precios positivos, bid ≤ ask y un row group por fecha.", "",
              "| activo | resultado | filas | sesiones |", "|---|---|---:|---:|"] + [f"| {v['instrument']} | {'OK' if v['ok'] else 'FALLA: ' + '; '.join(v['problems'])} | {v['rows']:,} | {v['sessions']} |" for v in ver] + [""]
    L += ["## 3. Auditoría de lo que había publicado en Kaggle", "",
          f"Contraste sesión por sesión (trades por contrato y fecha de trading) de {len(kb)} archivos Parquet publicados contra los originales locales: {tot.get('EQUAL', 0):,} sesiones idénticas, {tot.get('CLOSE', 0):,} casi idénticas (< 1 %), "
          f"{tot.get('DIFF', 0):,} con diferencias y {tot.get('KAGGLE_ONLY', 0):,} que existen en Kaggle sin original de texto local (casi todo RTY y tramos tempranos de MYM/MES/MNQ/YM). Ninguna sesión de holdout en lo publicado. "
          "Detalle por archivo: `kaggle_vs_sources_by_file.csv` (en la carpeta de trabajo, sin precios).", "",
          "## 4. Resolución de los 23 problemas del handoff", "", "| ID | prioridad | problema | estado | evidencia | residual |", "|---|---|---|---|---|---|"]
    for i, p, t, s, e, r in LOG:
        L.append(f"| {i} | {p} | {t} | `{s}` | {e.format(**fmt)} | {r.format(**fmt)} |")
    L += ["", "## 5. Decisiones que quedan en manos de Nico", "",
          "1. **Aprobar o corregir la política de liquidez** (`metadata/liquidity_policy.json`). Hasta entonces la release es candidata.",
          "2. **Licencia/redistribución de los datos CME** (todo está en privado).",
          "3. **Exportar lo que falta** (`MISSING_EXPORTS.md`): RTY completo, MYM y los fines de septiembre de varios activos.",
          "4. **Calendario histórico oficial de CME** para cerrar D06 y distinguir feriados de huecos de export.", "",
          "## 6. Espacio de Kaggle", "", "Mapa, estados y kernels agrupados por familia: `KAGGLE_SPACE_INDEX.md` (dentro de `edgelab-data-catalog`) y `config/kaggle_space_map_20261014.json`. Ningún dataset ni kernel se borró; sólo se señalizaron metadatos.", ""]
    out = Path(a.out)
    (out / "LIQUID_RELEASE_20261014.md").write_text("\n".join(L), encoding="utf-8")
    (out / "ISSUE_RESOLUTION_LOG_20261014.json").write_text(json.dumps(
        [dict(id=i, priority=p, problem=t, status=s, evidence=e.format(**fmt), residual=r.format(**fmt)) for i, p, t, s, e, r in LOG],
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("informe escrito")


if __name__ == "__main__":
    main()
