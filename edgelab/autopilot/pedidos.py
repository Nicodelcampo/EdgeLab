"""Pedidos a un humano (pedido de Nico, 2026-10-19): cuando el agente necesita algo que sólo una persona puede dar
(datos que faltan, una exportación de NT8, un dataset privado, una credencial, una decisión), lo PIDE por un canal
estructurado en vez de quedarse trabado en silencio.

- `pedidos_humano.jsonl` (append-only, se sube a autopilot/state): cada pedido con id estable, tipo, qué, por qué,
  qué bloquea, quién lo pidió (módulo) y estado (ABIERTO / RESUELTO). El mismo pedido no se duplica: se refresca.
- Cada pedido nuevo se anuncia en la sala (`sala_outbox.jsonl`) y, si está configurado, en EDGELAB_ALERT_URL.
- Se cierra desde la sala con `resuelto <id> [nota]` (persona autorizada) o a mano con `cerrar()`.
Los pedidos nunca contienen secretos ni rutas locales: describen QUÉ hace falta, no dónde está.
"""
from __future__ import annotations
import hashlib, json, os, time, urllib.request
from pathlib import Path

TIPOS = ("datos", "exportacion_nt8", "credencial", "decision", "infraestructura", "otro")
ARCHIVO = "pedidos_humano.jsonl"


def _append(p: Path, row: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def estado(root: Path) -> dict:
    """id -> último registro del pedido."""
    p = Path(root) / ARCHIVO; d = {}
    if p.exists():
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.strip(): r = json.loads(l); d[r["id"]] = {**d.get(r["id"], {}), **r}
    return d


def abiertos(root: Path) -> list:
    return [r for r in estado(root).values() if r.get("estado") == "ABIERTO"]


def pedir(root: Path, tipo: str, que: str, por_que: str, bloquea: str = "", origen: str = "autopilot", ahora=None) -> dict:
    if tipo not in TIPOS: raise ValueError(f"tipo desconocido: {tipo}")
    root = Path(root); ahora = ahora or time.time()
    pid = "P-" + hashlib.sha256(f"{tipo}|{que}".encode()).hexdigest()[:8]
    prev = estado(root).get(pid)
    if prev and prev.get("estado") == "ABIERTO":                     # ya pedido: no se repite el aviso
        return prev
    row = dict(id=pid, ts=ahora, tipo=tipo, que=que, por_que=por_que, bloquea=bloquea, origen=origen, estado="ABIERTO")
    _append(root / ARCHIVO, row)
    texto = f"PEDIDO {pid} ({tipo}): {que}. Por qué: {por_que}." + (f" Bloquea: {bloquea}." if bloquea else "") + f" Responder en la sala: resuelto {pid}"
    _append(root / "sala_outbox.jsonl", dict(ts=ahora, fuente="pedido", texto=texto, pedido=pid))
    url = os.environ.get("EDGELAB_ALERT_URL")
    if url:
        try: urllib.request.urlopen(urllib.request.Request(url, data=f"EdgeLab {texto}".encode(), method="POST"), timeout=10)
        except Exception: pass
    return row


def cerrar(root: Path, pid: str, quien: str, nota: str = "", ahora=None) -> bool:
    ids = {k.lower(): k for k in estado(root)}                        # la sala pasa el texto en minúsculas
    pid = ids.get(pid.strip().lower())
    if pid is None: return False
    _append(Path(root) / ARCHIVO, dict(id=pid, ts=ahora or time.time(), estado="RESUELTO", resuelto_por=quien, nota=nota))
    return True


def desde_ciclo(root: Path, rep: dict) -> list:
    """Convierte bloqueos del ciclo que sólo resuelve una persona en pedidos (datos faltantes en Kaggle, envío incierto)."""
    out = []
    for b in rep.get("blocked", []) or []:
        rid, motivos = (b[0], b[1]) if isinstance(b, (list, tuple)) and len(b) > 1 else (str(b), "")
        txt = json.dumps(motivos, ensure_ascii=False) if not isinstance(motivos, str) else motivos
        if any(k in txt.lower() for k in ("falta", "sin fuente", "no existe", "missing", "no hay datos")):
            out.append(pedir(root, "datos", f"datos para la corrida {rid}", txt[:400], bloquea=f"lanzamiento de {rid}", origen="daemon"))
    return out
