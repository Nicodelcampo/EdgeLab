"""Orquestador Multi-Agente Debian v2 (`edgelab/autopilot/orquestador_multiagente.py`).

Implementa en código ejecutable la arquitectura seleccionada para el servidor Debian (`SV1`):
  - **Capa 0 — Capataz Determinista (`Python puro`, cada 10 min)**:
    Sincroniza `CODE_DIR` con `origin/foundation/f0b-compatibility-probe` (`sincronizador_ramas.py`), avanza el embudo,
    balancea los 8 slots de Kaggle entre `nicolasbuttaro` y `nicobuttaro`, ejecuta `auditor_alineacion.py` (10 SLIs)
    y administra la máquina de estados de la Guarda `O16` (`VERIFICANDO_O16`).
  - **Agente 1 — Arquitecto Cuantitativo, Meta-Analista e Investigador (`Claude Opus 4.6`)**:
    Recibe el paquete de contexto jerárquico amplio (`armar_contexto_amplio_espiral`, hasta `80.000` chars sin el bucle
    `pop()` destructivo que borraba fichas y vacíos), aplica el criterio **Velocidad vs. Cuidado** (`evaluar_velocidad_cuidado`)
    y emite campañas o pedidos de código apoyados en `catalogo_espiral.py`.
  - **Agente 2 — Ingeniero de Módulos, Optimizador Numba y Doctor Autorreparador (`Claude Opus 4.6` en `git worktree`)**:
    Ejecuta `programador.py` con los 4 controles sintéticos (`ruido`, `plantado`, `oráculo`, `causal`), preflight estático/dinámico,
    compuerta de densidad local (`E0 >= 30 ops`) y verificación obligatoria del primer kernel relanzado tras reparar una
    campaña `BLOQUEADA` (`Guarda O16`).
  - **Agente 3 — Auditor Adversario, Guardián de Alineación y Cronista (`Claude Sonnet 4.6`)**:
    Ejecuta revisión adversaria rápida (`auditar_propuesta_sonnet`) antes de gastar cuota de Kaggle (verificando invarianza
    de escala, multiplicidad, frontera `holdout.desde == 20261001` de Directiva #6 y reservas LORD++), audita los 10 SLIs
    de alineación y redacta la crónica verificable para la sala.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from edgelab.research import catalogo_espiral as CE, embudo, holdout_ventanas as HV, linaje

TOPOLOGIA_DEBIAN_V2: dict[str, Any] = {
    "schema": "edgelab_topologia_multiagente_debian_v2",
    "arquitectura_seleccionada": "CAPATAZ_PYTHON + 2_OPUS_4_6 + 1_SONNET_4_6",
    "justificacion_seleccion": (
        "Un solo agente sufre sesgo de autoconfirmación y agota contexto mezclando estrategia con depuración Numba; "
        "1 Opus + 1 Sonnet deja al único Opus como juez y parte de su propio código; 2 Opus puros encarece y enlentece "
        "los chequeos adversarios de alta frecuencia. La tríada 2 Opus 4.6 (Arquitecto + Ingeniero/Doctor aislados) + "
        "1 Sonnet 4.6 (Auditor Adversario, Alineación 10-SLI y Cronista) sobre el Capataz Python determinista maximiza "
        "rigor, velocidad, creatividad y separación de poderes."
    ),
    "agentes": {
        "capa_0_capataz": {
            "motor": "python_determinista",
            "cadencia_min": 10,
            "responsabilidades": [
                "Sincronización automática con origin/foundation/f0b-compatibility-probe (sincronizador_ramas.py)",
                "Avance determinista del embudo (Embudo.avanzar_todas) con balanceo 8 slots en 2 cuentas Kaggle",
                "Ejecución de los 10 SLIs de auditor_alineacion.py y apertura de tickets de reparación",
                "Seguimiento del estado VERIFICANDO_O16 tras cada reapertura de campaña",
            ],
        },
        "agente_1_arquitecto": {
            "modelo": "claude-opus-4-6",
            "rol": "Arquitecto Cuantitativo, Meta-Analista e Investigador en Espiral",
            "max_chars_contexto": 80000,
            "herramientas": ["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
            "responsabilidades": [
                "Analizar APRENDIZAJES_ESPIRAL.md, RESUMEN.json del analizador y metaanalisis_embudo.py",
                "Combinar bloques de catalogo_espiral.py (L1 + L2 + regimen) y biblioteca de ideas",
                "Clasificar cada diseño mediante la compuerta Velocidad vs. Cuidado (VIA_RAPIDA_COMPOSICION vs VIA_CUIDADA_PARIDAD)",
                "Emitir especificaciones de campaña y pedidos de código sin tocar el checkout vivo",
            ],
        },
        "agente_2_ingeniero_doctor": {
            "modelo": "claude-opus-4-6",
            "rol": "Ingeniero de Módulos Numba y Doctor Autorreparador en Worktree",
            "max_chars_contexto": 80000,
            "herramientas": ["Read", "Edit", "Write", "Glob", "Grep", "Bash(pytest)", "Bash(preflight)"],
            "responsabilidades": [
                "Implementar experimentos en git worktree aislada reutilizando primitivas de catalogo_espiral.py",
                "Aprobar los 4 controles sintéticos (ruido, plantado, oráculo, causal) + preflight + densidad E0 >= 30 ops",
                "Diagnosticar logs reales de campañas BLOQUEADAS, reparar causa raíz, reconstruir kernels (O6) y activar VERIFICANDO_O16",
            ],
        },
        "agente_3_auditor_cronista": {
            "modelo": "claude-sonnet-4-6",
            "rol": "Auditor Adversario Pre-Lanzamiento, Guardián de Alineación (10 SLIs) y Cronista",
            "max_chars_contexto": 48000,
            "herramientas": ["Read", "Grep", "Glob"],
            "responsabilidades": [
                "Ejecutar abogado_del_diablo y auditar_propuesta_sonnet antes de autorizar corridas en Kaggle",
                "Verificar cumplimiento de Directivas 1 a 7 (holdout.desde == 20261001, linaje declarado, invarianza de escala)",
                "Publicar dictamen de alineación y crónica clara en sala_outbox.jsonl",
            ],
        },
    },
}


@dataclass
class EvaluacionVelocidadCuidado:
    via: str  # "VIA_RAPIDA_COMPOSICION" | "VIA_CUIDADA_PARIDAD"
    requiere_oraculo_numba: bool
    requiere_prueba_densidad_e0: bool
    min_ops_e0_requeridas: int
    tiempo_max_kernel_min: int
    controles_exigidos: list[str]
    motivo: str

    def a_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluar_velocidad_cuidado(
    *,
    usa_detector_nuevo_numba: bool,
    reutiliza_primitivas_l1_l2: list[str],
    n_celdas_por_canal: int,
    cruza_instrumento_nuevo: bool = False,
) -> EvaluacionVelocidadCuidado:
    """Determina con criterio objetivo si un diseño va por Vía Rápida (composición de primitivas ya probadas)
    o por Vía Cuidada (nuevo detector microestructural / paridad C# / grilla > 500k celdas).
    """
    controles = ["test_control_ruido", "test_control_plantado", "test_causal", "preflight_estatico"]
    if usa_detector_nuevo_numba or n_celdas_por_canal > 500_000 or not reutiliza_primitivas_l1_l2:
        controles.extend(["test_oraculo_python_vs_numba", "preflight_dinamico_sintetico", "densidad_e0_local_10_sesiones"])
        return EvaluacionVelocidadCuidado(
            via="VIA_CUIDADA_PARIDAD",
            requiere_oraculo_numba=True,
            requiere_prueba_densidad_e0=True,
            min_ops_e0_requeridas=30,
            tiempo_max_kernel_min=90,
            controles_exigidos=controles,
            motivo=(
                "Introduce detector @njit nuevo o supera 500k celdas/canal: exige oráculo Python vs Numba, "
                "preflight dinámico y verificación de densidad E0 >= 30 operaciones antes de lanzar en Kaggle."
            ),
        )
    if cruza_instrumento_nuevo:
        controles.append("verificacion_invarianza_escala_cuantiles")
    return EvaluacionVelocidadCuidado(
        via="VIA_RAPIDA_COMPOSICION",
        requiere_oraculo_numba=False,
        requiere_prueba_densidad_e0=True,
        min_ops_e0_requeridas=30,
        tiempo_max_kernel_min=45,
        controles_exigidos=controles,
        motivo=(
            f"Composición directa de primitivas L1/L2 ya validadas ({', '.join(reutiliza_primitivas_l1_l2)}) "
            f"con {n_celdas_por_canal:,} celdas/canal: lanzamiento ágil tras preflight y control de densidad E0."
        ),
    )


def armar_contexto_amplio_espiral(
    *,
    directivas_texto: str,
    resumen_catalogo: str,
    aprendizajes_espiral: str,
    tablero: dict[str, Any],
    cartas_gramatica: list[dict[str, Any]],
    vacios: list[Any],
    fichas_existentes: list[dict[str, Any]],
    max_chars: int = 80000,
) -> dict[str, Any]:
    """Construye el paquete de contexto amplio para el Arquitecto Opus 4.6 con presupuesto garantizado por sección.
    Nunca elimina secciones completas mediante `pop()` ciego: comprime proporcionalmente cada lista si el total
    supera `max_chars`, preservando siempre Directivas, Catálogo en Espiral, Aprendizajes, Cartas, Vacíos y Fichas.
    """
    presupuesto_aprendizajes = max(8000, int(max_chars * 0.25))
    presupuesto_catalogo = max(6000, int(max_chars * 0.15))

    paquete: dict[str, Any] = {
        "directivas_vigentes": directivas_texto[:6000],
        "topologia_multiagente": {
            "arquitectura": TOPOLOGIA_DEBIAN_V2["arquitectura_seleccionada"],
            "regla_espiral": "Apoyar toda familia nueva en primitivas de catalogo_espiral.py y hallazgos de APRENDIZAJES_ESPIRAL.md",
        },
        "catalogo_modulos_espiral": resumen_catalogo[:presupuesto_catalogo],
        "aprendizajes_espiral_recientes": aprendizajes_espiral[-presupuesto_aprendizajes:],
        "tablero_embudo": tablero,
        "cartas_gramatica": list(cartas_gramatica[:12]),
        "vacios_cobertura": list(vacios[:40]),
        "fichas_codigo_reutilizable": list(fichas_existentes[:40]),
    }

    # Si supera max_chars, recorta gradualmente la longitud de las listas manteniendo al menos 8 elementos en cada una
    while len(json.dumps(paquete, ensure_ascii=False)) > max_chars:
        if len(paquete["fichas_codigo_reutilizable"]) > 10:
            paquete["fichas_codigo_reutilizable"] = paquete["fichas_codigo_reutilizable"][:-5]
        elif len(paquete["vacios_cobertura"]) > 10:
            paquete["vacios_cobertura"] = paquete["vacios_cobertura"][:-5]
        elif len(paquete["aprendizajes_espiral_recientes"]) > 4000:
            paquete["aprendizajes_espiral_recientes"] = paquete["aprendizajes_espiral_recientes"][-4000:]
        else:
            break

    return paquete


def auditar_propuesta_sonnet(spec_campana: dict[str, Any]) -> dict[str, Any]:
    """Revisión adversaria determinista + reglas del Agente 3 (Sonnet 4.6) antes de autorizar una campaña en Kaggle."""
    objeciones: list[str] = []
    avisos: list[str] = []

    # 1. Chequeo de problemas de embudo (períodos, frontera holdout, conteo exacto de n_celdas_por_canal)
    probs_emb = embudo.problemas_campana(spec_campana)
    if probs_emb:
        objeciones.extend([f"embudo: {p}" for p in probs_emb])

    # 2. Chequeo de Directiva #6 (holdout.desde == 20261001 si OOS cerró <= 20260930 sin ventana consumida en octubre)
    oos = spec_campana.get("oos") or [0, 0]
    h_desde = int((spec_campana.get("holdout") or {}).get("desde", 0))
    fam = str(spec_campana.get("familia", ""))
    if int(oos[1]) <= 20260930 and HV.ultima_consumida(fam) is None and h_desde != 20261001:
        objeciones.append(f"Directiva #6: OOS cierra en {oos[1]} sin consumo en octubre, pero holdout.desde={h_desde} (!= 20261001)")

    # 3. Chequeo de Linaje declarado en LINAJES.jsonl
    probs_lin = linaje.problemas(fam)
    if probs_lin:
        objeciones.extend([f"linaje: {p}" for p in probs_lin])

    # 4. Chequeo de justificación económica y refutación explícita
    if len(str(spec_campana.get("justificacion_economica", "")).strip()) < 40:
        objeciones.append("Falta justificacion_economica sustantiva (>= 40 chars explicando mecanismo y contraparte)")
    if len(str(spec_campana.get("como_podria_refutarse", "")).strip()) < 30:
        objeciones.append("Falta como_podria_refutarse concreto (>= 30 chars)")

    # 5. Chequeo de reparto dual de cuentas Kaggle (Directiva #4)
    cuenta = spec_campana.get("cuenta_kaggle")
    if cuenta not in ("auto", "nicolasbuttaro", "nicobuttaro"):
        avisos.append(f"cuenta_kaggle={cuenta!r}: se recomienda 'auto' para balancear entre nicolasbuttaro y nicobuttaro")

    return {
        "aprobada": len(objeciones) == 0,
        "cid": spec_campana.get("cid"),
        "familia": fam,
        "objeciones": objeciones,
        "avisos": avisos,
    }


def registrar_reapertura_o16(state_dir: Path, cid: str, commit_fix: str, causa_raiz: str) -> dict[str, Any]:
    """Registra una campaña reabierta bajo la Guarda O16 (`VERIFICANDO_O16`): exige verificar el primer kernel relanzado."""
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    ruta = state_dir / "verificaciones_o16.json"
    datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    registro = {
        "cid": cid,
        "estado_o16": "VERIFICANDO_O16",
        "commit_fix": commit_fix,
        "causa_raiz": causa_raiz,
        "ts_reapertura": time.time(),
        "primer_kernel_verificado": False,
    }
    datos[cid] = registro
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return registro


def verificar_cierre_o16(state_dir: Path, cid: str, estado_kernel: str, log_kernel: str) -> dict[str, Any]:
    """Verifica el resultado del primer kernel tras una reapertura (`Guarda O16`)."""
    ruta = Path(state_dir) / "verificaciones_o16.json"
    datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    reg = datos.get(cid, {"cid": cid, "estado_o16": "VERIFICANDO_O16"})
    if estado_kernel == "complete" and "Traceback" not in log_kernel:
        reg["estado_o16"] = "VERIFICADA_OK"
        reg["primer_kernel_verificado"] = True
    elif estado_kernel in ("error", "failed") or "Traceback" in log_kernel:
        reg["estado_o16"] = "RECAIDA_DETECTADA"
        reg["primer_kernel_verificado"] = False
        reg["ultimo_error"] = log_kernel[-400:]
    datos[cid] = reg
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return reg
