#!/usr/bin/env python3
"""Vigilante EXTERNO del autopilot: corre en su propio timer, así detecta lo que el ciclo no puede ver de sí mismo.
Mira: latido viejo, unidades systemd fallidas, envíos inciertos y pausas activas. Cada alerta va a:
  - `alertas.jsonl` (append-only, se sube a autopilot/state: trazable);
  - `sala_outbox.jsonl` (la lee el agente de Chaski);
  - opcional: POST a EDGELAB_ALERT_URL (p. ej. un tópico de ntfy), si está en /etc/edgelab/autopilot.env.
No repite la misma alerta más de una vez cada 6 horas.
  python tools/autopilot_watchdog.py --state DIR [--max-latido 3600] [--falla UNIDAD]"""
import argparse, json, os, subprocess, time, urllib.request
from pathlib import Path

UNIDADES = ("edgelab-autopilot.service", "edgelab-autopilot-generate.service", "edgelab-propfirm-refresh.service")
REPETIR_S = 6 * 3600


def _append(p: Path, row: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")


def revisar(state: Path, max_latido: int, ahora: float, systemctl=True) -> list:
    out = []
    hb = state / "heartbeat.json"
    if not hb.exists(): out.append(("sin_latido", "no hay heartbeat.json: el ciclo nunca corrió"))
    else:
        h = json.loads(hb.read_text()); edad = ahora - float(h.get("ts", 0))
        if edad > max_latido: out.append(("latido_viejo", f"último ciclo hace {edad / 60:.0f} min (máx {max_latido / 60:.0f})"))
        if h.get("send_uncertain"): out.append(("envio_incierto", f"conciliar a mano, nunca reenviar: {h['send_uncertain']}"))
    for nombre in ("PAUSE", "PAUSE_SALA"):
        for p in (state / nombre, state.parent.parent / nombre):
            if p.exists() and ahora - p.stat().st_mtime > 24 * 3600: out.append(("pausa_larga", f"{p} existe hace más de 24 h"))
    if systemctl:
        for u in UNIDADES:
            r = subprocess.run(["systemctl", "is-failed", "--quiet", u], capture_output=True)
            if r.returncode == 0: out.append(("unidad_fallida", f"{u} en estado failed: journalctl -u {u}"))
    return out


def emitir(state: Path, alertas: list, ahora: float) -> list:
    memo_p = state / "watchdog_memo.json"; memo = json.loads(memo_p.read_text()) if memo_p.exists() else {}
    nuevas = []
    for clave, texto in alertas:
        k = f"{clave}:{texto}"
        if ahora - memo.get(k, 0) < REPETIR_S: continue
        memo[k] = ahora; row = dict(ts=ahora, alerta=clave, texto=texto, fuente="watchdog"); nuevas.append(row)
        _append(state / "alertas.jsonl", row); _append(state / "sala_outbox.jsonl", dict(ts=ahora, fuente="watchdog", texto=f"ALERTA {clave}: {texto}"))
        url = os.environ.get("EDGELAB_ALERT_URL")
        if url:
            try: urllib.request.urlopen(urllib.request.Request(url, data=f"EdgeLab {clave}: {texto}".encode(), method="POST"), timeout=10)
            except Exception as e: _append(state / "alertas.jsonl", dict(ts=ahora, alerta="envio_alerta_fallido", texto=repr(e)[:200]))
    memo_p.write_text(json.dumps(memo))
    return nuevas


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--state", required=True); ap.add_argument("--max-latido", type=int, default=3600); ap.add_argument("--falla")
    a = ap.parse_args(); st = Path(a.state); ahora = time.time()
    al = [("unidad_fallida", f"{a.falla} falló (OnFailure): journalctl -u {a.falla}")] if a.falla else revisar(st, a.max_latido, ahora)
    print(json.dumps(emitir(st, al, ahora), ensure_ascii=False))


if __name__ == "__main__":
    main()
