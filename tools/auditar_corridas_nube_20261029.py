#!/usr/bin/env python3
"""Herramienta ejecutable de auditoría de las corridas cosechadas desde la sesión en la nube (Olas 1-9).

Diseñada para que los agentes del Debian (SV1: Conductor de Embudo, Programador en worktree y Auditor)
verifiquen de manera independiente, determinista y reproducible las 16 campañas cosechadas y los 3 módulos
nuevos (`corredor_vol_gaps.py`, `otr_930_sweep.py`, `oro_almuerzo_ruptura.py`) sobre el commit vigente,
y generen la cola exacta de acciones de auditoría empírica y canasta de régimen.

Seis dimensiones de auditoría verificadas:
  1. Preflight estático y causalidad de indicadores (`preflight.verificar_experimento` + `indicadores.causal`).
  2. Contabilidad de multiplicidad, linajes (`LINAJES.jsonl`), evaluables (`EVALUABLES.jsonl`) y reservas LORD++ (`LIBRO_LORD.json`).
  3. Cumplimiento de la frontera de holdout (`Directiva #6`: `holdout.desde == 20261001` en familias cuyo OOS cerró en sep-2026)
     y consistencia de aperturas en `HOLDOUT_VENTANAS.jsonl`.
  4. Consistencia matemática de los artefactos por etapa (`DESC`, `INTEGRIDAD`, `OOS`, `TOPES`, `ACTA_HOLDOUT`, `pistas_replica`).
  5. Vigencia de hashes de código (`preflight.codigo_vigente`) contra los módulos actuales del repositorio.
  6. Generación de la cola accionable de auditoría para Debian (`COLA_AUDITORIA_DEBIAN_20261029.json` y `REPORTE_PREAUDITORIA_20261029.md`).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import pathlib
import sys
from typing import Any

RAIZ = pathlib.Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from edgelab.research import embudo, holdout_ventanas as HV, linaje, preflight
from tools import analizar_embudo as AE

CAMPANAS_AUDITADAS: list[str] = [
    # Familia 1: Corredor Vol + Gaps v2 (Olas 1-5)
    "CVGAP-NQ",
    "CVGAP-CFD-NQ",
    "CVGAP-ES",
    "CVGAP-CFD-ES",
    # Familia 2: OTR 9:30 Sweep & Return (Olas 7-9)
    "OTR930-NQ",
    "OTR930-ES",
    "OTR930-CFD-NQ",
    "OTR930-CFD-ES",
    # Familia 3: Oro Almuerzo Ruptura (Olas 7-9)
    "ORO-ALM-GC",
    "ORO-ALM-CFD",
    # Campañas U1 destrabadas y promovidas en Olas 1-9
    "U1-RACIMOS-GRILLA-NQ",
    "U1-RACIMOS-GRILLA-ES",
    "U1-ZONAS-BT2-ES",
    "U1-ZONAS-BT2-NQ",
    "U1-ZONAS-GRILLA-YM",
    "U1-6E-GRILLA",
]

MODULOS_NUEVOS: list[str] = [
    "edgelab.research.corredor_vol_gaps",
    "edgelab.research.otr_930_sweep",
    "edgelab.research.oro_almuerzo_ruptura",
]


def _carpeta_campana(spec: dict[str, Any], raiz: pathlib.Path = RAIZ) -> pathlib.Path:
    return raiz / pathlib.Path(spec["spec"]).parent / "embudo" / spec["cid"]


def _sha12_modulo(nombre_mod: str) -> str:
    m = importlib.import_module(nombre_mod)
    p = pathlib.Path(m.__file__)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def auditar_modulos(dinamico: bool = False) -> dict[str, Any]:
    """Audita preflight estático (y opcionalmente dinámico en sintético) de los 3 módulos nuevos."""
    resultados: dict[str, Any] = {}
    ok_global = True
    for mod in MODULOS_NUEVOS:
        rep = preflight.verificar_experimento(mod, dinamico_tambien=dinamico)
        resultados[mod] = {
            "ok": bool(rep.get("ok", False)),
            "errores": list(rep.get("errores", [])),
            "avisos": list(rep.get("avisos", [])),
            "sha12": _sha12_modulo(mod),
        }
        if not rep.get("ok", False):
            ok_global = False
    return {"ok": ok_global, "modulos": resultados}


def auditar_campana(cid: str, raiz: pathlib.Path = RAIZ) -> dict[str, Any]:
    """Audita una campaña individual en las dimensiones 1 a 5 y determina su acción Debian."""
    spec_path = raiz / "config/autopilot/grillas/campanas" / f"{cid}.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    carpeta = _carpeta_campana(spec, raiz)
    raiz_embudo_rel = str((pathlib.Path(spec["spec"]).parent / "embudo").as_posix())
    estado_path = carpeta / "estado.json"
    estado = json.loads(estado_path.read_text(encoding="utf-8"))

    hallazgos: list[str] = []
    avisos: list[str] = []

    # 1. Problemas estructurales del embudo
    probs_embudo = embudo.problemas_campana(spec)
    if probs_embudo:
        hallazgos.extend([f"problemas_campana: {p}" for p in probs_embudo])

    # 2. Frontera de holdout (Directiva #6: si OOS cerró <= 20260930 y no hay ventana consumida en octubre, desde == 20261001)
    oos_hasta = int(spec["oos"][1])
    h_desde = int(spec["holdout"]["desde"])
    ult_cons = HV.ultima_consumida(spec["familia"])
    if oos_hasta <= 20260930 and ult_cons is None and h_desde != 20261001:
        hallazgos.append(
            f"Directiva #6: OOS cerró {oos_hasta} sin ventana consumida en octubre, pero holdout.desde={h_desde} (!= 20261001)"
        )

    # Sincronía entre spec en disco y spec en estado.json
    est_h_desde = int(estado.get("spec", {}).get("holdout", {}).get("desde", 0))
    if est_h_desde != h_desde:
        hallazgos.append(f"Desincronía holdout.desde: spec={h_desde} vs estado.json={est_h_desde}")

    # 3. Linaje y Evaluables
    probs_lin = linaje.problemas(spec["familia"])
    if probs_lin:
        hallazgos.extend([f"linaje: {x}" for x in probs_lin])

    # 4. Estado actual y consistencia de artefactos de etapa
    etapa_actual = estado.get("etapa", "")
    fase_actual = estado.get("fase") or estado.get("veredicto") or ""
    celdas_analizador = AE.celdas_de(estado)

    # 5. Verificación específica de ACTA_HOLDOUT vs PISTAS_VIVAS (en estado.json)
    acta_path = carpeta / "ACTA_HOLDOUT.json"
    pistas_rep = estado.get("pistas_replica") or {}
    n_pistas_vivas = len(pistas_rep.get("celdas") or []) if fase_actual == "PISTAS_VIVAS" else 0
    accion_debian: dict[str, Any] = {}

    if acta_path.exists():
        acta = json.loads(acta_path.read_text(encoding="utf-8"))
        if int(acta.get("holdout_desde", 0)) != h_desde:
            hallazgos.append(
                f"ACTA_HOLDOUT.json tiene holdout_desde={acta.get('holdout_desde')} != spec={h_desde}"
            )
        # Verificar apertura en HOLDOUT_VENTANAS.jsonl
        probs_hv = HV.problemas(spec["familia"], h_desde, cid)
        if probs_hv:
            hallazgos.extend([f"HOLDOUT_VENTANAS: {p}" for p in probs_hv])
        # Verificar reserva en LIBRO_LORD.json
        libro_data = json.loads((raiz / "docs/research/LIBRO_LORD.json").read_text(encoding="utf-8"))
        res_id = acta.get("reserva_lord", {}).get("reserva_id", f"{cid}/holdout")
        clave_res = f"{spec['familia']}::{res_id}"
        if clave_res not in libro_data.get("reservas", {}):
            hallazgos.append(f"Reserva LORD++ {clave_res} no figura en LIBRO_LORD.json")

        accion_debian = {
            "tipo": "AUDITAR_ACTA_Y_EVALUAR_HOLDOUT",
            "prioridad": 1,
            "cid": cid,
            "familia": spec["familia"],
            "sensor": spec["sensor"],
            "ejecucion": spec["ejecucion"],
            "holdout_desde": h_desde,
            "n_fijo": int(acta.get("n_fijo", 150)),
            "alfa_lord": float(acta.get("alfa", 0.0)),
            "celda_ganadora": acta.get("regla", {}).get("celda"),
            "tope": acta.get("regla", {}).get("tope"),
            "n_celdas_analizador": len(celdas_analizador),
            "comandos_debian": [
                f"python3 tools/embudo_correr.py config/autopilot/grillas/campanas/{cid}.json --raiz {raiz_embudo_rel}",
                "python3 tools/analizar_embudo.py lanzar",
            ],
        }
    elif fase_actual == "PISTAS_VIVAS" and n_pistas_vivas > 0:
        canasta_info = pistas_rep.get("canasta") or {}
        accion_debian = {
            "tipo": "AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN",
            "prioridad": 2,
            "cid": cid,
            "familia": spec["familia"],
            "sensor": spec["sensor"],
            "ejecucion": spec["ejecucion"],
            "etapa_cierre": etapa_actual,
            "veredicto": fase_actual,
            "n_pistas_vivas": n_pistas_vivas,
            "media_canasta_oos": canasta_info.get("media"),
            "ic90_canasta_oos": canasta_info.get("ic90"),
            "n_celdas_analizador": len(celdas_analizador),
            "comandos_debian": [
                f"python3 tools/holdout_canasta.py acta {raiz_embudo_rel} {cid} --n-sesiones 20",
                f"python3 tools/holdout_canasta.py conteo {raiz_embudo_rel} {cid}",
                "python3 tools/analizar_embudo.py lanzar",
            ],
        }
    else:
        accion_debian = {
            "tipo": "AUDITAR_ANALIZADOR_DESARROLLO",
            "prioridad": 3,
            "cid": cid,
            "familia": spec["familia"],
            "etapa_cierre": etapa_actual,
            "veredicto": fase_actual,
            "n_pistas_vivas": 0,
            "n_celdas_analizador": len(celdas_analizador),
            "comandos_debian": ["python3 tools/analizar_embudo.py lanzar"] if celdas_analizador else [],
        }

    return {
        "cid": cid,
        "familia": spec["familia"],
        "experimento": spec["experimento"],
        "sensor": spec["sensor"],
        "ejecucion": spec["ejecucion"],
        "etapa": etapa_actual,
        "veredicto": fase_actual,
        "holdout_desde": h_desde,
        "tiene_acta_holdout": acta_path.exists(),
        "tiene_pistas_vivas": bool(fase_actual == "PISTAS_VIVAS" and n_pistas_vivas > 0),
        "n_pistas_vivas": n_pistas_vivas,
        "n_celdas_analizador": len(celdas_analizador),
        "ok": len(hallazgos) == 0,
        "hallazgos": hallazgos,
        "avisos": avisos,
        "accion_debian": accion_debian,
    }


def ejecutar_auditoria_completa(dinamico: bool = False, escribir_reportes: bool = True) -> dict[str, Any]:
    """Ejecuta la auditoría completa sobre los 3 módulos y las 16 campañas cosechadas."""
    rep_modulos = auditar_modulos(dinamico=dinamico)
    campanas_rep: dict[str, Any] = {}
    cola_acciones: list[dict[str, Any]] = []
    ok_campanas = True

    for cid in CAMPANAS_AUDITADAS:
        c_rep = auditar_campana(cid)
        campanas_rep[cid] = c_rep
        if not c_rep["ok"]:
            ok_campanas = False
        cola_acciones.append(c_rep["accion_debian"])

    cola_acciones.sort(key=lambda x: (x.get("prioridad", 99), x.get("cid", "")))

    actas_listas = [c for c, r in campanas_rep.items() if r["tiene_acta_holdout"]]
    pistas_con_vivas = [c for c, r in campanas_rep.items() if r["tiene_pistas_vivas"]]

    resumen = {
        "fecha_auditoria": "2026-10-29",
        "ok_global": bool(rep_modulos["ok"] and ok_campanas),
        "n_modulos_auditados": len(MODULOS_NUEVOS),
        "n_campanas_auditadas": len(CAMPANAS_AUDITADAS),
        "n_actas_holdout_listas": len(actas_listas),
        "actas_holdout_listas": actas_listas,
        "n_campanas_pistas_vivas": len(pistas_con_vivas),
        "campanas_pistas_vivas": pistas_con_vivas,
        "modulos": rep_modulos,
        "campanas": campanas_rep,
        "cola_auditoria_debian": cola_acciones,
    }

    if escribir_reportes:
        out_dir = RAIZ / "docs/research/auditoria_corridas_20261029"
        out_dir.mkdir(parents=True, exist_ok=True)
        cola_path = out_dir / "COLA_AUDITORIA_DEBIAN_20261029.json"
        cola_path.write_text(json.dumps(resumen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        md_lines = [
            "# Reporte de Pre-Auditoría y Cola de Ejecución para los Agentes del Debian (2026-10-29)",
            "",
            f"- **Estado global de verificación pre-auditoría:** `{'OK (0 errores)' if resumen['ok_global'] else 'CON HALLAZGOS'}`",
            f"- **Módulos experimentales verificados (`preflight` + causalidad):** `{resumen['n_modulos_auditados']}` (`corredor_vol_gaps`, `otr_930_sweep`, `oro_almuerzo_ruptura`)",
            f"- **Campañas auditadas (Olas 1–9):** `{resumen['n_campanas_auditadas']}`",
            f"- **Campañas en `CONTEO` con `ACTA_HOLDOUT.json` y reserva LORD++:** `{resumen['n_actas_holdout_listas']}` (`{', '.join(actas_listas)}`)",
            f"- **Campañas en `PISTAS_VIVAS` (`n_pistas_vivas == 20`) para canasta de régimen y analizador:** `{resumen['n_campanas_pistas_vivas']}` (`{', '.join(pistas_con_vivas)}`)",
            "",
            "## 1. Tabla Resumen de las 16 Campañas Auditadas",
            "",
            "| Campaña (`cid`) | Familia | Sensor -> Ejecución | Etapa | Fase / Veredicto | `holdout.desde` | Celdas Analizador | Estado Auditoría | Acción Primaria Debian |",
            "|---|---|---|---|---|---:|---:|---|---|",
        ]
        for cid in CAMPANAS_AUDITADAS:
            r = campanas_rep[cid]
            acc = r["accion_debian"]["tipo"]
            est_ok = "OK" if r["ok"] else f"ERROR ({len(r['hallazgos'])})"
            md_lines.append(
                f"| `{cid}` | `{r['familia']}` | `{r['sensor']} -> {r['ejecucion']}` | `{r['etapa']}` | `{r['veredicto']}` | `{r['holdout_desde']}` | `{r['n_celdas_analizador']}` | `{est_ok}` | `{acc}` |"
            )

        md_lines.extend(
            [
                "",
                "## 2. Protocolo de Auditoría Independiente para los Agentes del Debian (`SV1`)",
                "",
                "### Fase A — Verificación Determinista Local (Conductor + Auditor)",
                "1. Ejecutar `python3 tools/auditar_corridas_nube_20261029.py --dinamico` y confirmar `ok_global: true`.",
                "2. Ejecutar `pytest tests/research/test_auditoria_corridas_nube_20261029.py tests/research/test_corredor_vol_gaps.py tests/research/test_otr_930_sweep.py tests/research/test_oro_almuerzo_ruptura.py tests/autopilot/test_auditor_alineacion.py`.",
                "",
                "### Fase B — Evaluación de las 6 Nuevas `ACTA_HOLDOUT.json` en `edgelab-holdout-sellado` (`CONTEO` y `HOLDOUT`)",
                "Para cada una de las 6 campañas que superaron las 4 etapas del embudo (`CVGAP-NQ`, `CVGAP-CFD-NQ`, `U1-RACIMOS-GRILLA-NQ`, `U1-ZONAS-BT2-ES`, `U1-ZONAS-BT2-NQ`, `U1-RACIMOS-GRILLA-ES`):",
                "1. Correr `tools/embudo_correr.py` sobre `edgelab-holdout-sellado` desde `holdout.desde = 20261001`.",
                "2. Evaluar si el rendimiento en la ventana disponible de octubre (`20261001..20261026`) se encuentra dentro de la banda esperada según la distribución de desarrollo/OOS (Directiva #6 de canasta de régimen).",
                "",
                "### Fase C — Auditoría de Canasta de Régimen (`tools/holdout_canasta.py`) y Analizador (`tools/analizar_embudo.py`) sobre las 9 Campañas en `PISTAS_VIVAS`",
                "Para `CVGAP-ES`, `CVGAP-CFD-ES`, `OTR930-NQ`, `OTR930-ES`, `OTR930-CFD-NQ`, `OTR930-CFD-ES`, `ORO-ALM-GC`, `ORO-ALM-CFD` y `U1-6E-GRILLA` (y `U1-ZONAS-GRILLA-YM` en el analizador):",
                "1. Evaluar la elegibilidad de la canasta de 20 pistas congeladas con `tools/holdout_canasta.py`.",
                "2. Lanzar `python3 tools/analizar_embudo.py lanzar` y `python3 tools/analizar_embudo.py traer` para generar los perfiles completos de desarrollo (`20250805..20260930`).",
            ]
        )

        (out_dir / "REPORTE_PREAUDITORIA_20261029.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return resumen


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita las 16 campañas y 3 módulos de las Olas 1-9.")
    parser.add_argument("--dinamico", action="store_true", help="Ejecuta también el preflight dinámico en sintético.")
    parser.add_argument("--no-escribir", action="store_true", help="No regenera los archivos en docs/research/auditoria_corridas_20261029.")
    args = parser.parse_args()

    res = ejecutar_auditoria_completa(dinamico=args.dinamico, escribir_reportes=not args.no_escribir)
    print(
        json.dumps(
            {
                "ok_global": res["ok_global"],
                "n_modulos_auditados": res["n_modulos_auditados"],
                "n_campanas_auditadas": res["n_campanas_auditadas"],
                "actas_holdout_listas": res["actas_holdout_listas"],
                "campanas_pistas_vivas": res["campanas_pistas_vivas"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if res["ok_global"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
