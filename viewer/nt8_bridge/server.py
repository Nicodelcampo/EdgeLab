import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

class NoCacheServer(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
    server = HTTPServer(('0.0.0.0', port), NoCacheServer)
    print(f"Serving HTTP on 0.0.0.0 port {port} with No-Cache headers...")
    server.serve_forever()
