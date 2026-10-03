"""Servidor local del prototipo (solo archivos estáticos, sin caché).
Uso: python design/prototypes/ui-professional/serve.py [puerto]   (por defecto 5290)"""
import http.server, os, sys

class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

os.chdir(os.path.dirname(os.path.abspath(__file__)))
port = int(sys.argv[1]) if len(sys.argv) > 1 else 5290
print(f"Prototipo de diseño: http://127.0.0.1:{port}/")
http.server.ThreadingHTTPServer(("127.0.0.1", port), NoCache).serve_forever()
