"""Puente con la sala de Chaski (F5 del plan). Archivos, no red: el agente de Chaski que corre en SV1 los lee y escribe.

- `sala_outbox.jsonl`: un renglón por ciclo con `hechos` (números sacados del ledger, nunca del LLM) y `texto` para la sala.
  El texto lo redacta el rol cronista si hay `RoleRunner`; si no, una plantilla fija. Los números viajan siempre aparte.
- `sala_inbox.jsonl`: comandos que el agente de Chaski deja, de personas autorizadas: `pausa`, `reanudar`, `estado`, `aprobar <id>`, `pedidos`, `resuelto <id> [nota]`.
  `pausa`/`reanudar` actúan sólo sobre el interruptor de la sala (PAUSE_SALA): nunca levantan una pausa de consola.
  El campo `autor` no está firmado: el inbox se rechaza entero si otros usuarios o el grupo pueden escribirlo (debe ser 0600/0644 del usuario de Chaski).
  `aprobar` sólo se registra: no cambia el modo ni promueve candidatas (eso sigue siendo commit + promote de un humano).
"""
from __future__ import annotations
import json, os, time
from pathlib import Path

COMANDOS = {"pausa", "reanudar", "estado", "aprobar", "resuelto", "pedidos"}


def _append(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def hechos(tick: dict, status: dict) -> dict:
    """Sólo números y ids, copiados del reporte del ciclo y del estado del ledger."""
    return dict(evento=tick.get("event"), lanzada=tick.get("launched"), propuesta=tick.get("proposed"),
                cerradas=tick.get("closed", []), bloqueadas=[b[0] for b in tick.get("blocked", [])],
                modo=status.get("mode"), pausado=status.get("paused"), alfa=round(float(status.get("alpha_wealth") or 0), 6),
                corriendo=[r.get("run_id") for r in status.get("running", [])], envio_incierto=status.get("send_uncertain", []),
                diagnostico=tick.get("diagnostico", []), pedidos_abiertos=status.get("pedidos_abiertos", []))


def plantilla(h: dict) -> str:
    partes = [f"Ciclo: {h['evento']}. Modo {h['modo']}{' (pausado)' if h['pausado'] else ''}. Alfa disponible {h['alfa']}."]
    if h["lanzada"]: partes.append(f"Lanzada: {h['lanzada'][0]}.")
    if h["propuesta"]: partes.append(f"Propuesta (sin lanzar): {h['propuesta'][0]}.")
    if h["cerradas"]: partes.append("Cerradas: " + ", ".join(f"{c[0]}={c[1]}" for c in h["cerradas"]) + ".")
    if h["corriendo"]: partes.append("Corriendo: " + ", ".join(h["corriendo"]) + ".")
    if h["envio_incierto"]: partes.append("ATENCIÓN, envío incierto (conciliar a mano): " + ", ".join(map(str, h["envio_incierto"])) + ".")
    if h["bloqueadas"]: partes.append(f"Bloqueadas por guardas: {len(h['bloqueadas'])}.")
    if h.get("pedidos_abiertos"): partes.append("Pedidos a humano abiertos: " + ", ".join(h["pedidos_abiertos"]) + " (responder: resuelto <id>).")
    for d in h.get("diagnostico", []):
        if not d["automatica"]: partes.append(f"REQUIERE HUMANO: {d['sintoma']} -> {d['accion']}.")
    return " ".join(partes)


def reportar(root: Path, tick: dict, status: dict, runner=None, now=None) -> dict:
    h = hechos(tick, status)
    texto, fuente = plantilla(h), "plantilla"
    if runner is not None:
        r = runner.call("cronista", {"hechos": h})
        if r.get("status") in ("OK", "CACHED"):
            texto, fuente = r["output"]["resumen_sala"], "cronista"
    row = dict(ts=now or time.time(), hechos=h, texto=texto, fuente=fuente)
    _append(Path(root) / "sala_outbox.jsonl", row)
    return row


def aplicar_comandos(root: Path, kill_switch: Path, autorizados, status_fn, now=None) -> list:
    """Lee los comandos nuevos (offset persistido). Ignora autores no autorizados y comandos desconocidos, y deja constancia."""
    root = Path(root); inbox = root / "sala_inbox.jsonl"; off_path = root / "sala_inbox.offset"
    if not inbox.exists(): return []
    if os.name == "posix" and inbox.stat().st_mode & 0o022:          # permisos POSIX (Debian); en Windows st_mode no refleja las ACL
        _append(root / "sala_outbox.jsonl", dict(ts=now or time.time(), fuente="seguridad", texto="sala_inbox.jsonl escribible por grupo u otros: comandos ignorados"))
        return [("inbox_inseguro", oct(inbox.stat().st_mode & 0o777))]
    off = int(off_path.read_text()) if off_path.exists() else 0
    lines = inbox.read_text(encoding="utf-8").splitlines()
    hechos_cmd = []
    for raw in lines[off:]:
        try: c = json.loads(raw)
        except json.JSONDecodeError: hechos_cmd.append(("invalido", None)); continue
        autor, texto = str(c.get("autor", "")), str(c.get("texto", "")).strip().lower()
        cmd, _, arg = texto.partition(" ")
        if autor not in set(autorizados): hechos_cmd.append(("no_autorizado", autor)); continue
        if cmd not in COMANDOS: hechos_cmd.append(("desconocido", cmd)); continue
        if cmd == "pausa": Path(kill_switch).parent.mkdir(parents=True, exist_ok=True); Path(kill_switch).touch()
        elif cmd == "reanudar": Path(kill_switch).unlink(missing_ok=True)
        elif cmd == "estado": _append(root / "sala_outbox.jsonl", dict(ts=now or time.time(), estado=status_fn(), fuente="estado"))
        elif cmd == "resuelto":
            from .pedidos import cerrar
            pid, _, nota = arg.strip().partition(" ")
            ok = cerrar(root, pid, autor, nota, ahora=now)
            _append(root / "sala_outbox.jsonl", dict(ts=now or time.time(), fuente="pedido", texto=f"{pid}: {'cerrado' if ok else 'id desconocido'} por {autor}"))
        elif cmd == "pedidos":
            from .pedidos import abiertos
            _append(root / "sala_outbox.jsonl", dict(ts=now or time.time(), fuente="pedido", texto="Pedidos abiertos: " + ("; ".join(f"{p['id']} {p['que']}" for p in abiertos(root)) or "ninguno")))
        elif cmd == "aprobar": _append(root / "sala_aprobaciones.jsonl", dict(ts=now or time.time(), autor=autor, id=arg.strip(), efecto="ninguno: sólo registro"))
        hechos_cmd.append((cmd, autor))
    off_path.write_text(str(len(lines)))
    return hechos_cmd
