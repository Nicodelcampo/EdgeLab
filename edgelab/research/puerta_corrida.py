"""Puerta unica pre-corrida (Capas 1-4 de persistencia de contexto fail-closed).

Orquesta en una sola llamada determinista:
  L1: invariantes de holdout y vigencia de `docs/ESTADO_VIVO.md`;
  L2: contrato y preflight sintetico del modulo canonico;
  L3: memoria activa (`NO_REPETIR`, linajes e invalidaciones) + holdout consumido;
  L4: validacion del pre-registro, registro global K51 y exit-gate de kernel.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from edgelab import holdout as HO
from edgelab.edge_brain.invalidation import DependencyEdge
from edgelab.research import holdout_ventanas as HV
from edgelab.research.contexto_vivo import verificar_estado_vivo
from edgelab.research.memoria_activa import verificar_memoria_activa
from edgelab.research.preflight import validar_preregistro
from edgelab.research.puerta_kernel import validar_modulo_sintetico, validar_script_kernel

ROOT = Path(__file__).resolve().parents[2]


def _esta_en_registro_global(prereg_path: Path, root: Path) -> bool:
    reg = root / "docs" / "research" / "TRIAL_REGISTRY_GLOBAL.jsonl"
    if not reg.exists():
        return False
    try:
        rel = prereg_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = prereg_path.as_posix()
    notas = {
        str(json.loads(l).get("note", "")).replace("\\", "/")
        for l in reg.read_text(encoding="utf-8").splitlines()
        if l.strip()
    }
    return rel in notas


def verificar_corrida(
    *,
    prereg: str | Path | None = None,
    modulo: str | None = None,
    familia: str | None = None,
    script: str | Path | None = None,
    exigir_contada: bool = False,
    correr_sintetico: bool = False,
    verificar_estado: bool = True,
    dependencias: Iterable[DependencyEdge] | None = None,
    ids_invalidados: Iterable[str] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Ejecuta las 4 capas de verificacion pre-corrida y retorna veredicto estructurado."""
    repo = Path(root) if root is not None else ROOT
    errores: list[str] = []
    avisos: list[str] = []
    capas: dict[str, dict[str, Any]] = {}

    # Capa 1: Runtime & Holdout + Estado Vivo
    e1: list[str] = []
    if int(HO.HOLDOUT_PRIMERA_SESION_INT) != 20261001:
        e1.append(f"frontera holdout inesperada: {HO.HOLDOUT_PRIMERA_SESION_INT}")
    if verificar_estado:
        e1.extend(verificar_estado_vivo(repo))
    capas["L1_runtime"] = {"ok": not e1, "errores": e1}
    errores.extend(e1)

    # Capa 2: Runner canonico y preflight sintetico
    e2: list[str] = []
    if modulo:
        if correr_sintetico:
            e2.extend(validar_modulo_sintetico(modulo))
        else:
            import importlib
            mod = importlib.import_module(modulo)
            if callable(getattr(mod, "eventos", None)):
                from edgelab.research import tablas as TB
                e2.extend(TB.contrato(mod))
            elif callable(getattr(mod, "disparos", None)):
                from edgelab.research import preflight as PF
                e2.extend(PF.estatico(mod))
            else:
                e2.append(f"{modulo} no expone `eventos` ni `disparos`")
    capas["L2_runner"] = {"ok": not e2, "errores": e2}
    errores.extend(e2)

    # Capa 3: Memoria activa (NO_REPETIR, linajes e invalidaciones) + holdout previo
    e3: list[str] = []
    prereg_text = ""
    prereg_p: Path | None = None
    if prereg is not None:
        prereg_p = Path(prereg)
        prereg_p = prereg_p if prereg_p.is_absolute() else repo / prereg_p
        if prereg_p.exists():
            prereg_text = prereg_p.read_text(encoding="utf-8", errors="ignore")
    if prereg_text or familia:
        e3.extend(
            verificar_memoria_activa(
                prereg_text,
                familia=familia,
                root=repo,
                dependencias=dependencias,
                ids_invalidados=ids_invalidados,
            )
        )
    if familia:
        lib_hv = repo / "docs" / "research" / "HOLDOUT_VENTANAS.jsonl"
        aps = HV.aperturas_vigentes(familia, lib_hv)
        if aps:
            avisos.append(f"familia {familia} ya uso su apertura confirmatoria: {[a['cid'] for a in aps]}")
        ult = HV.ultima_consumida(familia, lib_hv)
        if ult is not None:
            avisos.append(f"familia/linaje {familia} tiene sesiones holdout consumidas hasta {ult}")
    capas["L3_memoria_activa"] = {"ok": not e3, "errores": e3}
    errores.extend(e3)

    # Capa 4: Pre-registro, contador global K51 y puerta de salida del kernel
    e4: list[str] = []
    if prereg_p is not None:
        e4.extend(validar_preregistro(prereg_p, repo=repo, exigir_commit=exigir_contada))
        if exigir_contada and not _esta_en_registro_global(prereg_p, repo):
            e4.append(f"K51: {prereg_p.name} no esta contado en docs/research/TRIAL_REGISTRY_GLOBAL.jsonl")
    if script is not None:
        sp = Path(script)
        sp = sp if sp.is_absolute() else repo / sp
        if not sp.exists():
            e4.append(f"script no existe: {script}")
        else:
            e4.extend(validar_script_kernel(sp.read_text(encoding="utf-8", errors="ignore"), require_canonical=True))
    capas["L4_salida"] = {"ok": not e4, "errores": e4}
    errores.extend(e4)

    return {
        "ok": not errores,
        "capas": capas,
        "errores": errores,
        "avisos": avisos,
    }
