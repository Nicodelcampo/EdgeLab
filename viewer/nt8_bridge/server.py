import json
import re
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

LABELS = Path(__file__).resolve().parent / "labels"
SAFE = re.compile(r"^[A-Za-z0-9_\-]{1,80}$")


class NoCacheServer(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_POST(self):
        # Única escritura permitida: etiquetas humanas en labels/<nombre>.json (JSON válido, <= 5 MB, nombre seguro).
        m = re.match(r"^/api/labels/([^/]+)$", self.path)
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not m or not SAFE.match(m.group(1)) or n <= 0 or n > 5_000_000:
            self.send_error(400, "ruta o tamaño no permitido"); return
        try:
            obj = json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            self.send_error(400, "JSON inválido"); return
        LABELS.mkdir(exist_ok=True)
        import threading
        tmp = LABELS / f"{m.group(1)}.json.{threading.get_ident()}.partial"   # un temporal por hilo: sin carreras
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(LABELS / f"{m.group(1)}.json")
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(b'{"ok":true}')


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).resolve().parent)          # sirve siempre la carpeta del visor
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
    server = ThreadingHTTPServer(('127.0.0.1', port), NoCacheServer)
    print(f"Serving HTTP on 127.0.0.1 port {port} with No-Cache headers (POST /api/labels/<nombre>)...")
    server.serve_forever()
