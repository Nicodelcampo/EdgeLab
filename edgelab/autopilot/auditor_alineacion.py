"""Auditor determinista y multi-agente de alineación operativa para el Debian (SV1).

Verifica en cada ciclo que el comportamiento real del agente en SV1 cumpla con:
- config/autopilot/DIRECTIVAS.md
- docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md (O1..O16, E1..E10)
- Separación estricta CODE_DIR vs STATE_DIR y sincronía con foundation/f0b-compatibility-probe
- Funcionamiento de la espiral (APRENDIZAJES_ESPIRAL.md, programador activo, 8 slots en 2 cuentas)
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckAlineacion:
    codigo: str
    nombre: str
    ok: bool
    severidad: str  # "CRITICA" | "ALTA" | "MEDIA"
    detalle: str
    accion_correctiva: str


@dataclass
class ReporteAlineacion:
    ts: float
    head_code: str
    target_branch: str
    puntaje_salud: float
    checks: list[CheckAlineacion] = field(default_factory=list)
    acciones_pendientes: list[str] = field(default_factory=list)

    def a_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "head_code": self.head_code,
            "target_branch": self.target_branch,
            "puntaje_salud": round(self.puntaje_salud, 4),
            "checks": [asdict(c) for c in self.checks],
            "acciones_pendientes": list(self.acciones_pendientes),
        }

    def a_markdown(self) -> str:
        lineas = [
            "# Reporte Automático de Alineación del Agente Debian (`SV1`)",
            f"- **HEAD activo**: `{self.head_code}` (rama objetivo: `{self.target_branch}`)",
            f"- **Puntaje de salud operativa**: `{self.puntaje_salud:.1%}`",
            "",
            "| Código | Verificación | Estado | Severidad | Detalle | Acción Correctiva |",
            "|---|---|---|---|---|---|",
        ]
        for c in self.checks:
            estado = "OK" if c.ok else "DESVÍO"
            lineas.append(
                f"| `{c.codigo}` | {c.nombre} | **{estado}** | {c.severidad} | {c.detalle} | {c.accion_correctiva} |"
            )
        return "\n".join(lineas) + "\n"


def evaluar_alineacion_estado(
    *,
    head_local: str,
    head_remoto: str,
    archivos_sucios_code: list[str],
    config_autopilot: dict[str, Any],
    unidades_fallidas: list[str],
    existe_aprendizajes_espiral: bool,
    campanas_bloqueadas_sin_ticket: list[str],
    reaperturas_sin_verificacion_o16: list[str],
    max_chars_contexto: int = 64000,
) -> ReporteAlineacion:
    """Evalúa los 8 invariantes operativos de alineación de SV1."""
    checks: list[CheckAlineacion] = []

    # 1. Sincronía Git con la rama troncal
    ok_git = bool(head_local and head_local == head_remoto)
    checks.append(
        CheckAlineacion(
            codigo="SLI-01",
            nombre="Sincronía automática con rama troncal",
            ok=ok_git,
            severidad="CRITICA",
            detalle=f"local={head_local[:8]} vs remoto={head_remoto[:8]}",
            accion_correctiva="Ejecutar deploy/debian/auto_sync_code.sh antes del ciclo." if not ok_git else "Ninguna",
        )
    )

    # 2. Árbol de código limpio (separación CODE_DIR vs STATE_DIR)
    ok_clean = len(archivos_sucios_code) == 0
    checks.append(
        CheckAlineacion(
            codigo="SLI-02",
            nombre="Árbol de código limpio (sin estado vivo en CODE_DIR)",
            ok=ok_clean,
            severidad="CRITICA",
            detalle="0 archivos sucios" if ok_clean else f"{len(archivos_sucios_code)} sucios: {archivos_sucios_code[:3]}",
            accion_correctiva="Redirigir EVALUABLES/LIBRO_LORD/launches a STATE_DIR." if not ok_clean else "Ninguna",
        )
    )

    # 3. Programador autónomo activo (Directiva #5)
    prog_cfg = config_autopilot.get("programador") or {}
    ok_prog = bool(prog_cfg.get("activo") is True)
    checks.append(
        CheckAlineacion(
            codigo="SLI-03",
            nombre="Programador autónomo activo (Agente 2 Opus)",
            ok=ok_prog,
            severidad="ALTA",
            detalle=f"programador.activo={prog_cfg.get('activo')}",
            accion_correctiva="Activar programador.activo=true y edgelab-autopilot-programador.timer." if not ok_prog else "Ninguna",
        )
    )

    # 4. Concurrencia 8 en 2 cuentas de Kaggle (Directiva de escala)
    kag_cfg = config_autopilot.get("kaggle") or {}
    max_conc = int(kag_cfg.get("max_concurrent") or 0)
    cuentas = kag_cfg.get("accounts") or []
    ok_kag = max_conc >= 8 and len(cuentas) >= 2
    checks.append(
        CheckAlineacion(
            codigo="SLI-04",
            nombre="Presupuesto Kaggle 8 slots repartidos en 2 cuentas",
            ok=ok_kag,
            severidad="ALTA",
            detalle=f"max_concurrent={max_conc}, cuentas={len(cuentas)}",
            accion_correctiva="Configurar max_concurrent=8 y tokens de nicolasbuttaro + nicobuttaro." if not ok_kag else "Ninguna",
        )
    )

    # 5. Servicios systemd sin estado failed
    ok_systemd = len(unidades_fallidas) == 0
    checks.append(
        CheckAlineacion(
            codigo="SLI-05",
            nombre="Unidades systemd sanas (sin estado failed)",
            ok=ok_systemd,
            severidad="ALTA",
            detalle="Todas activas" if ok_systemd else f"Fallidas: {unidades_fallidas}",
            accion_correctiva="Ejecutar systemctl reset-failed y revisar journalctl." if not ok_systemd else "Ninguna",
        )
    )

    # 6. Memoria en espiral presente y actualizada (Directiva #2)
    checks.append(
        CheckAlineacion(
            codigo="SLI-06",
            nombre="Memoria acumulativa APRENDIZAJES_ESPIRAL.md presente",
            ok=existe_aprendizajes_espiral,
            severidad="MEDIA",
            detalle="Presente en docs/research/APRENDIZAJES_ESPIRAL.md" if existe_aprendizajes_espiral else "Ausente",
            accion_correctiva="Generar y actualizar docs/research/APRENDIZAJES_ESPIRAL.md tras cada tanda." if not existe_aprendizajes_espiral else "Ninguna",
        )
    )

    # 7. Guarda O16 (verificación de primer kernel tras reapertura) y atención a BLOQUEADAS
    ok_o16 = len(campanas_bloqueadas_sin_ticket) == 0 and len(reaperturas_sin_verificacion_o16) == 0
    checks_det = (
        "Sin campañas bloqueadas desatendidas ni reaperturas sin verificar"
        if ok_o16
        else f"bloqueadas={campanas_bloqueadas_sin_ticket}, sin_o16={reaperturas_sin_verificacion_o16}"
    )
    checks.append(
        CheckAlineacion(
            codigo="SLI-07",
            nombre="Autorreparación y Guarda O16 en reaperturas",
            ok=ok_o16,
            severidad="CRITICA",
            detalle=checks_det,
            accion_correctiva="Inspeccionar log del primer kernel relanzado y emitir ticket al Doctor Opus." if not ok_o16 else "Ninguna",
        )
    )

    # 8. Contexto amplio sin truncamiento ciego de fichas/gramática
    ok_ctx = max_chars_contexto >= 48000
    checks.append(
        CheckAlineacion(
            codigo="SLI-08",
            nombre="Presupuesto de contexto amplio para el Arquitecto Opus",
            ok=ok_ctx,
            severidad="MEDIA",
            detalle=f"max_chars={max_chars_contexto}",
            accion_correctiva="Elevar max_chars >= 64000 con compresión estructurada por secciones." if not ok_ctx else "Ninguna",
        )
    )

    pesos = {"CRITICA": 3.0, "ALTA": 2.0, "MEDIA": 1.0}
    total_peso = sum(pesos[c.severidad] for c in checks)
    peso_ok = sum(pesos[c.severidad] for c in checks if c.ok)
    puntaje = peso_ok / total_peso if total_peso > 0 else 1.0
    acciones = [f"[{c.codigo}] {c.accion_correctiva}" for c in checks if not c.ok]

    return ReporteAlineacion(
        ts=time.time(),
        head_code=head_local,
        target_branch=head_remoto,
        puntaje_salud=puntaje,
        checks=checks,
        acciones_pendientes=acciones,
    )
