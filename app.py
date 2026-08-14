"""
app.py - Servidor Web Local y Backend API para el Asistente Digital Movistar
Utiliza la librería estándar de Python (http.server) para una ejecución sin dependencias.
"""

import os
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from diff_engine import auditar_variacion_recibo
from nbo_engine import generar_next_best_offer
from database import get_connection, get_cliente_by_id

PORT = int(os.environ.get("PORT", 5000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class MovistarDashboardHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP para servir la interfaz web y endpoints de API."""

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        params = urllib.parse.parse_qs(parsed_url.query)

        # 1. Ruta Principal: Dashboard Web
        if path == "/" or path == "/index.html":
            html_path = os.path.join(BASE_DIR, "templates", "index.html")
            if os.path.exists(html_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(html_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Template index.html no encontrado.")
                return

        # 2. Archivos Estáticos CSS / JS
        if path.startswith("/static/"):
            file_path = os.path.join(BASE_DIR, path.lstrip("/"))
            if os.path.exists(file_path):
                self.send_response(200)
                if file_path.endswith(".css"):
                    self.send_header("Content-Type", "text/css; charset=utf-8")
                elif file_path.endswith(".js"):
                    self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        # 3. Endpoint API: /api/diff (Auditoría de Variación de Recibos)
        if path == "/api/diff":
            id_cliente = params.get("id_cliente", ["CLI001"])[0]
            periodo = params.get("periodo", ["2026-07"])[0]
            resultado = auditar_variacion_recibo(id_cliente, periodo)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))
            return

        # 4. Endpoint API: /api/nbo (Next Best Offer & Movistar Total)
        if path == "/api/nbo":
            cliente_id = params.get("cliente_id", ["1000001"])[0]
            resultado = generar_next_best_offer(cliente_id)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))
            return

        # 5. Endpoint API: /api/cliente (Detalle del Cliente)
        if path == "/api/cliente":
            cliente_id = params.get("cliente_id", ["1000001"])[0]
            try:
                cid = int(str(cliente_id).replace("CLI", ""))
                cliente = get_cliente_by_id(cid)
            except Exception:
                cliente = None

            self.send_response(200 if cliente else 404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(cliente or {"encontrado": False}, ensure_ascii=False).encode("utf-8"))
            return

        # Fallback a archivos estáticos predeterminados
        super().do_GET()


def run_server(port: int = PORT):
    server_address = ("", port)
    httpd = HTTPServer(server_address, MovistarDashboardHandler)
    print(f"============================================================")
    print(f"Servidor Web Movistar Dashboard iniciado exitosamente.")
    print(f"URL Local: http://localhost:{port} (o http://127.0.0.1:{port})")
    print(f"Presiona Ctrl+C para detener el servidor.")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
