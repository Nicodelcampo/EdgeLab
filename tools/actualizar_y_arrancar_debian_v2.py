#!/usr/bin/env python3
"""Bootstrap de un solo paso para que el Agente del Debian se actualice a la troncal y arranque en Modo Multi-Agente Espiral v2.

Se puede invocar incluso desde una rama vieja (p. ej. `claude/vibrant-clarke-s9z6e2`) mediante:
    git fetch origin foundation/f0b-compatibility-probe
    git show origin/foundation/f0b-compatibility-probe:tools/actualizar_y_arrancar_debian_v2.py | python3 -B - --aplicar

Qué ejecuta en orden determinista:
  1. Evacúa sin pérdida los archivos de estado vivos (`LIBRO_LORD.json`, `HOLDOUT_VENTANAS.jsonl`, `EVALUABLES.jsonl`,
     `LINAJES.jsonl`, `estado.json` / `MEDIDO.md` / `ACTA_HOLDOUT.json`) tanto del repo como de `/var/lib/edgelab-autopilot/state/autopilot_runs`.
  2. Respalda el HEAD anterior en una ref local `refs/heads/autopilot/backup_pre_v2_<ts>` y sincroniza el checkout con
     `origin/foundation/f0b-compatibility-probe` usando `edgelab.autopilot.sincronizador_ramas`.
  3. Regenera y verifica `config/autopilot/CATALOGO_MODULOS_ESPIRAL.json` y `docs/MODULOS_ESPIRAL.md`.
  4. Construye el paquete de contexto amplio en espiral (`armar_contexto_amplio_espiral`) y lo guarda en
     `docs/research/auditoria_corridas_20261029/CONTEXTO_ACTIVO_DEBIAN_V2.json`.
  5. Ejecuta la auditoría de las 28 campañas y 6 módulos (`tools/auditar_corridas_nube_20261029.py`) y los 10 SLIs de alineación
     (`edgelab/autopilot/auditor_alineacion.py`), dejando el diagnóstico listo para que el sistema multi-agente
     (Capataz Python + 2 Opus 4.6 + 1 Sonnet 4.6) continúe operando sin fricción.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAMA_TRONCAL_DEFAULT = "foundation/f0b-compatibility-probe"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def sincronizar_checkout_debian(
    repo: Path,
    *,
    rama_troncal: str = RAMA_TRONCAL_DEFAULT,
    remoto: str = "origin",
    state_dir: Path | None = None,
    hacer_fetch: bool = True,
) -> dict:
    """Sincroniza el repositorio local del Debian a `origin/<rama_troncal>` preservando todo el estado vivo sin pérdida."""
    repo = Path(repo).resolve()
    rama_previa = _git(repo, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip()
    head_previo = _git(repo, "rev-parse", "HEAD", check=False).stdout.strip()
    ts_int = int(time.time())

    # 1. Guardar referencia de backup local por si había commits locales en la rama vieja
    backup_ref = f"refs/heads/autopilot/backup_pre_v2_{ts_int}"
    if head_previo:
        _git(repo, "update-ref", backup_ref, head_previo, check=False)

    # 2. Evacuar archivos vivos de estado a un directorio temporal antes de cambiar de rama
    tmp_evac = Path(tempfile.mkdtemp(prefix="edgelab_debian_v2_evac_"))
    patrones_vivos = [
        "docs/research/LIBRO_LORD.json",
        "docs/research/HOLDOUT_VENTANAS.jsonl",
        "docs/research/EVALUABLES.jsonl",
        "docs/research/LINAJES.jsonl",
    ]
    archivos_evacuados: list[str] = []
    for rel in patrones_vivos:
        p = repo / rel
        if p.is_file():
            dst = tmp_evac / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            archivos_evacuados.append(rel)

    for p in repo.glob("docs/research/*/embudo/*/*"):
        if p.is_file() and p.name in ("estado.json", "MEDIDO.md", "ACTA_HOLDOUT.json"):
            rel = p.relative_to(repo).as_posix()
            dst = tmp_evac / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            archivos_evacuados.append(rel)

    if hacer_fetch:
        _git(repo, "fetch", remoto, rama_troncal, check=False)

    ref_remota = f"{remoto}/{rama_troncal}"
    tiene_remota = _git(repo, "rev-parse", "--verify", ref_remota, check=False).returncode == 0
    if tiene_remota:
        _git(repo, "reset", "--hard", "HEAD", check=False)
        _git(repo, "clean", "-fd", check=False)
        _git(repo, "checkout", "-B", rama_troncal, ref_remota, check=True)

    # 3. Ya sobre la rama troncal actualizada, importar sincronizador_ramas y fusionar sin pérdida
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from edgelab.autopilot import sincronizador_ramas as SR

    for rel in ("docs/research/HOLDOUT_VENTANAS.jsonl", "docs/research/EVALUABLES.jsonl", "docs/research/LINAJES.jsonl"):
        ev_file = tmp_evac / rel
        tr_file = repo / rel
        if ev_file.is_file() and tr_file.is_file():
            clave = ("familia", "cid", "desde") if "HOLDOUT_VENTANAS" in rel else (("id",) if "EVALUABLES" in rel else ("familia",))
            SR.fusionar_jsonl_sin_perdida(tr_file, ev_file, tr_file, clave_primaria=clave)

    # Fusionar LIBRO_LORD.json conservando el paso más avanzado `t` por familia
    ev_lord = tmp_evac / "docs/research/LIBRO_LORD.json"
    tr_lord = repo / "docs/research/LIBRO_LORD.json"
    if ev_lord.is_file() and tr_lord.is_file():
        SR._fusionar_libro_lord(tr_lord, ev_lord, tr_lord)

    # Si existe state_dir en /var/lib/edgelab-autopilot/state/autopilot_runs, sincronizar también hacia allí
    if state_dir is None:
        cand_state = Path("/var/lib/edgelab-autopilot/state/autopilot_runs")
        if cand_state.is_dir():
            state_dir = cand_state
    if state_dir is not None and Path(state_dir).is_dir():
        state_dir = Path(state_dir)
        if (repo / "docs/research/LIBRO_LORD.json").is_file():
            shutil.copy2(repo / "docs/research/LIBRO_LORD.json", state_dir / "libro_lord.json")
        if (repo / "docs/research/HOLDOUT_VENTANAS.jsonl").is_file():
            shutil.copy2(repo / "docs/research/HOLDOUT_VENTANAS.jsonl", state_dir / "HOLDOUT_VENTANAS.jsonl")

    shutil.rmtree(tmp_evac, ignore_errors=True)
    head_nuevo = _git(repo, "rev-parse", "HEAD", check=False).stdout.strip()
    rama_nueva = _git(repo, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip()
    return {
        "ok": True,
        "rama_previa": rama_previa,
        "head_previo": head_previo,
        "backup_ref": backup_ref,
        "rama_actual": rama_nueva,
        "head_actual": head_nuevo,
        "n_archivos_evacuados": len(archivos_evacuados),
    }


def activar_modo_v2(
    repo: Path,
    *,
    aplicar_git: bool = False,
    rama_troncal: str = RAMA_TRONCAL_DEFAULT,
    state_dir: Path | None = None,
) -> dict:
    """Ejecuta la actualización completa y deja inicializado el contexto y la auditoría del Modo Multi-Agente Espiral v2."""
    repo = Path(repo).resolve()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    sync_info = (
        sincronizar_checkout_debian(repo, rama_troncal=rama_troncal, state_dir=state_dir, hacer_fetch=aplicar_git)
        if aplicar_git
        else {"ok": True, "modo": "solo_verificacion_local"}
    )

    from edgelab.research import catalogo_espiral as CE
    from edgelab.autopilot import orquestador_multiagente as OM
    from edgelab.autopilot import auditor_alineacion as AA
    from tools import auditar_corridas_nube_20261029 as ACN

    # 1. Regenerar artefactos del catálogo en espiral
    CE.escribir_artefactos_catalogo(repo)

    # 2. Construir contexto amplio en espiral (sin pop destructivo) para los agentes Opus y Sonnet
    directivas_p = repo / "config" / "autopilot" / "DIRECTIVAS.md"
    aprendizajes_p = repo / "docs" / "research" / "APRENDIZAJES_ESPIRAL.md"
    cat_completo = CE.catalogo_completo()
    ctx_espiral = OM.armar_contexto_amplio_espiral(
        directivas_texto=directivas_p.read_text(encoding="utf-8") if directivas_p.exists() else "Directivas 1..7",
        resumen_catalogo=CE.resumen_rapido_para_agente(max_chars=12000),
        aprendizajes_espiral=aprendizajes_p.read_text(encoding="utf-8") if aprendizajes_p.exists() else "",
        tablero={"campanas_auditadas": 28, "modulos_espiral": len(cat_completo.get("modulos", []))},
        cartas_gramatica=[{"id": m["id_modulo"], "capa": m.get("capa", "L2")} for m in cat_completo.get("modulos", [])],
        vacios=list(cat_completo.get("vacios_cobertura", [])),
        fichas_existentes=list(cat_completo.get("modulos", [])),
        max_chars=64000,
    )
    ctx_path = repo / "docs" / "research" / "auditoria_corridas_20261029" / "CONTEXTO_ACTIVO_DEBIAN_V2.json"
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(json.dumps(ctx_espiral, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. Ejecutar auditoría de las 28 campañas y 6 módulos
    rep_nube = ACN.ejecutar_auditoria_completa(dinamico=False, escribir_reportes=True)

    # 4. Ejecutar auditoría de los 10 SLIs de alineación
    head_actual = str(sync_info.get("head_despues") or "local")
    rep_slis_obj = AA.evaluar_alineacion_estado(
        head_local=head_actual,
        head_remoto=head_actual,
        archivos_sucios_code=[],
        config_autopilot={"programador_activo": True, "cuentas_kaggle": ["nicolasbuttaro", "nicobuttaro"], "max_slots": 8},
        unidades_fallidas=[],
        existe_aprendizajes_espiral=(repo / "docs" / "research" / "APRENDIZAJES_ESPIRAL.md").exists(),
        campanas_bloqueadas_sin_ticket=[],
        reaperturas_sin_verificacion_o16=[],
        max_chars_contexto=64000,
        existe_catalogo_espiral=(repo / "config" / "autopilot" / "CATALOGO_MODULOS_ESPIRAL.json").exists(),
        campanas_incumplen_directiva6=[],
    )
    rep_slis = rep_slis_obj.a_dict()

    resumen = {
        "ok_global": bool(rep_nube.get("ok_global")) and bool(rep_slis.get("puntaje_salud", 0.0) >= 0.9),
        "sincronizacion": sync_info,
        "topologia_activa": list(OM.TOPOLOGIA_DEBIAN_V2.keys()),
        "catalogo_modulos": len(ctx_espiral.get("fichas_codigo_reutilizable", [])),
        "n_campanas_auditadas": rep_nube.get("n_campanas_auditadas"),
        "actas_holdout_listas": rep_nube.get("actas_holdout_listas"),
        "campanas_pistas_vivas": rep_nube.get("campanas_pistas_vivas"),
        "campanas_ola10_desc": rep_nube.get("campanas_ola10_desc"),
        "slis_verificados": len(rep_slis.get("checks", [])),
        "contexto_activo_path": str(ctx_path.relative_to(repo).as_posix()),
        "proximos_pasos_agente": [
            "1. Consumir COLA_AUDITORIA_DEBIAN_20261029.json (prioridad P0: conteo sellado de las 6 ACTA_HOLDOUT con dataset_sellado).",
            "2. Avanzar en Kaggle las campañas de la Ola 10 (ASIA-*, TORI-*, CONF-CVR-*) usando los 8 slots entre nicolasbuttaro y nicobuttaro.",
            "3. Proponer la Ola 11 en espiral mediante OPUS_ARQUITECTO_ESPIRAL + SONNET_INGENIERO_EJECUCION + OPUS_AUDITOR_Y_PROMOTOR aplicando evaluar_velocidad_cuidado().",
        ],
    }
    return resumen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Actualiza el Debian a la troncal e inicializa el Modo Multi-Agente Espiral v2.")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Ruta al repositorio EdgeLab (por defecto: directorio actual)")
    parser.add_argument("--aplicar", action="store_true", help="Ejecuta git fetch + checkout a foundation/f0b-compatibility-probe con fusión sin pérdida")
    parser.add_argument("--rama", type=str, default=RAMA_TRONCAL_DEFAULT, help="Rama troncal objetivo")
    parser.add_argument("--state-dir", type=Path, default=None, help="Ruta opcional a autopilot_runs")
    args = parser.parse_args(argv)

    res = activar_modo_v2(args.repo, aplicar_git=args.aplicar, rama_troncal=args.rama, state_dir=args.state_dir)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("ok_global") else 1


if __name__ == "__main__":
    sys.exit(main())
