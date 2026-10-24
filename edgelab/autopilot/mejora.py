"""Mejora continua y autorreparación, con perímetro (pedido de Nico, 2026-10-16).

La mejora acompaña todos los procesos, en cuatro ámbitos: global, infraestructura de agentes, módulos y eficiencia.
Lo que el sistema puede hacer SOLO vs. lo que sólo puede PROPONER está fijado acá, no en un prompt:

| ámbito | se aplica solo | sólo se propone (PR + tests + revisión) |
|---|---|---|
| eficiencia | configuración de corrida si optimizer.compare da salida idéntica y >= 1,2x | cambios de código del motor |
| infraestructura | reintento de operaciones idempotentes (traer resultados, consultar estado) | todo lo demás |
| módulos | código nuevo dentro del perímetro del programador, con tests verdes y controles (programador.py) | cambios al motor compartido (rama autopilot/propuesta/*) |
| global (gates, FDR, holdout, mandato, protegidos) | nunca | nunca por el sistema: sólo humano |

Un sistema que pudiera aflojar sus propias reglas para "mejorar" su tasa de hallazgos estaría fabricando falsos positivos.
"""
from __future__ import annotations
import json, time
from pathlib import Path

AMBITOS = ("global", "infraestructura", "modulo", "eficiencia")
NUNCA = ("edgelab/autopilot/guard.py", "edgelab/autopilot/fdr.py", "config/autopilot/protected.json", "MANDATO.md",
         "config/autopilot/mandate.json", "docs/NORTH_STAR.md", "docs/edge_validation_contract.md")

# síntoma en el log/estado -> (causa probable, acción, ¿automática?)
REGLAS = {
    "fetch_failed": ("no se pudo traer el resultado (red o nombre de archivo de salida)", "se reintenta en el próximo ciclo; si persiste 3 ciclos, revisar result_files", True),
    "send_uncertain": ("caída durante un envío a Kaggle", "conciliar a mano con el handle exacto; nunca reenviar", False),
    "STOP_protected_changed": ("cambió un archivo protegido", "un humano revisa y refresca el manifiesto (tools/autopilot_protect.py)", False),
    "heartbeat_viejo": ("el ciclo no corre (timer, memoria o caída del host)", "revisar systemctl status y journal; el ciclo es idempotente", False),
    "rol_bloqueado": ("límite de la suscripción", "se espera al reset; lo numérico sigue", True),
    "alfa_agotada": ("sin riqueza de alfa", "no lanzar campañas nuevas; priorizar réplicas", True),
    "salida_invalida_llm": ("el rol devolvió JSON inválido dos veces", "revisar el esquema o el prompt del rol (propuesta de mejora de módulo)", False),
}


def diagnosticar(eventos: list, status: dict, ahora=None, heartbeat_max_s=3600) -> list:
    ahora = ahora or time.time(); out = []
    sintomas = [e.get("event") for e in eventos]
    if any(b and "no se pudo traer" in str(b) for e in eventos for b in e.get("blocked", [])): sintomas.append("fetch_failed")
    if status.get("send_uncertain"): sintomas.append("send_uncertain")
    if status.get("heartbeat_age_s") is not None and status["heartbeat_age_s"] > heartbeat_max_s: sintomas.append("heartbeat_viejo")
    if (status.get("alpha_wealth") or 1) < 1e-4: sintomas.append("alfa_agotada")
    for s in dict.fromkeys(x for x in sintomas if x in REGLAS):
        causa, accion, auto = REGLAS[s]
        out.append(dict(sintoma=s, causa_probable=causa, accion=accion, automatica=auto))
    return out


class RegistroMejoras:
    """Libro append-only de propuestas de mejora. Nada de acá modifica código."""
    def __init__(self, path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)

    def proponer(self, ambito: str, que: str, evidencia: str, archivos=(), aceptacion: str = "", origen: str = "sistema"):
        if ambito not in AMBITOS: raise ValueError("ámbito desconocido")
        tocados = [a for a in archivos if a in NUNCA]
        estado = "SOLO_HUMANO" if (ambito == "global" or tocados) else "PROPUESTA"
        row = dict(ts=time.time(), ambito=ambito, que=que, evidencia=evidencia, archivos=list(archivos), aceptacion=aceptacion or
                   {"eficiencia": "salida canónica idéntica y >= 1,2x (optimizer.compare)", "infraestructura": "tests verdes en Linux + doctor OK",
                    "modulo": "tests verdes + revisión de PR", "global": "decisión explícita de Nico"}[ambito], estado=estado, origen=origen)
        with self.path.open("a", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def abiertas(self):
        if not self.path.exists(): return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
