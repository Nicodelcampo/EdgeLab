"""Cliente MCP (HTTP «streamable», JSON-RPC) para StrategyQuant X y MetaTrader 5 desde EdgeLab (2026-11-14).

Uso:
  python tools/mcp_cliente.py sqx herramientas                     # lista las herramientas del servidor
  python tools/mcp_cliente.py sqx list_projects                    # llama una herramienta sin argumentos
  python tools/mcp_cliente.py sqx query_databank '{"name":"P","databank":"Results","limit":20}'
  python tools/mcp_cliente.py mt5 account_info

Servidores: URL en `EDGELAB_MCP_<NOMBRE>` (p. ej. EDGELAB_MCP_SQX=https://<túnel>/mcp); por defecto, los locales de la laptop
(SQX http://127.0.0.1:8080/mcp; MT5 terminal http://127.0.0.1:22346/mcp, MetaEditor :22345). Las credenciales NUNCA van acá:
en la nube las inyecta el proxy del entorno (secreto de red del host del túnel); en la laptop, `EDGELAB_MCP_<NOMBRE>_TOKEN` (Bearer).
Guardas: `execute_shell`/`run_python` de SQX y toda herramienta de MT5 que opere (órdenes) se rechazan salvo `--permitir-riesgo`.
Reglas de uso: docs/infra/SQX_MT5_EDGELAB_INFRA.md.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

DEFECTO = {"sqx": "http://127.0.0.1:8080/mcp", "mt5": "http://127.0.0.1:22346/mcp", "metaeditor": "http://127.0.0.1:22345/mcp"}
RIESGO = {"execute_shell", "run_python", "order_send", "order_check", "order_close", "positions_close", "order_modify", "order_cancel"}


class Cliente:
    def __init__(self, nombre: str):
        self.url = os.environ.get(f"EDGELAB_MCP_{nombre.upper()}", DEFECTO.get(nombre.lower(), ""))
        if not self.url: raise SystemExit(f"sin URL para {nombre}: definí EDGELAB_MCP_{nombre.upper()}")
        tok = os.environ.get(f"EDGELAB_MCP_{nombre.upper()}_TOKEN")
        self.h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", **({"Authorization": f"Bearer {tok}"} if tok else {})}
        self.sid, self.n = None, 0
        r = self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "edgelab", "version": "1"}})
        self.servidor = r.get("serverInfo", {})
        self._rpc("notifications/initialized", None, notif=True)

    def _rpc(self, metodo, params, notif=False, timeout=600):
        self.n += 1; cuerpo = {"jsonrpc": "2.0", "method": metodo, **({} if notif else {"id": self.n}), **({"params": params} if params is not None else {})}
        import time, urllib.error
        for intento in range(6):                           # el túnel o SQX ocupado devuelven 502/503/504: reintento con espera creciente
            req = urllib.request.Request(self.url, json.dumps(cuerpo).encode(), {**self.h, **({"mcp-session-id": self.sid} if self.sid else {})})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    self.sid = r.headers.get("mcp-session-id", self.sid); txt = r.read().decode("utf-8", "replace")
                break
            except urllib.error.HTTPError as e:
                if e.code == 404 and self.sid and metodo != "initialize" and intento < 5:   # sesión MCP vencida: reconectar y repetir
                    self.sid = None; self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "edgelab", "version": "1"}})
                    self._rpc("notifications/initialized", None, notif=True); continue
                if e.code not in (502, 503, 504) or intento == 5: raise
                time.sleep(2 ** intento)
        if notif: return None
        datos = [l[5:].strip() for l in txt.splitlines() if l.startswith("data:")] or [txt]
        msg = json.loads(datos[-1])
        if "error" in msg: raise RuntimeError(msg["error"])
        return msg["result"]

    def herramientas(self) -> list:
        return self._rpc("tools/list", {})["tools"]

    def llamar(self, herramienta: str, args: dict | None = None, permitir_riesgo: bool = False):
        if herramienta in RIESGO and not permitir_riesgo: raise SystemExit(f"{herramienta}: herramienta de riesgo (shell u órdenes); usar --permitir-riesgo sólo con OK humano")
        r = self._rpc("tools/call", {"name": herramienta, "arguments": args or {}})
        txt = "".join(c.get("text", "") for c in r.get("content", []) if c.get("type") == "text")
        if r.get("isError"): raise RuntimeError(txt)
        try: return json.loads(txt)
        except ValueError: return txt


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) < 2: raise SystemExit(__doc__)
    c = Cliente(a[0])
    if a[1] == "herramientas":
        for t in c.herramientas(): print(t["name"], "-", (t.get("description") or "")[:120])
        return
    r = c.llamar(a[1], json.loads(a[2]) if len(a) > 2 else {}, "--permitir-riesgo" in sys.argv)
    print(json.dumps(r, indent=1, ensure_ascii=False) if not isinstance(r, str) else r)


if __name__ == "__main__":
    main()
