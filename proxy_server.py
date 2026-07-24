#!/usr/bin/env python3
import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
FRONTEND_DIR = Path(__file__).parent / "astro-engine" / "frontend"

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path.startswith('/api/') or path.startswith('/webhooks/') or path.startswith('/download/'):
            return path
        return super().translate_path(path)

    def do_GET(self):
        if self.path.startswith('/api/') or self.path.startswith('/download/'):
            self.proxy_request()
        else:
            self.serve_static()

    def do_POST(self):
        if self.path.startswith('/api/') or self.path.startswith('/webhooks/'):
            self.proxy_request()
        else:
            self.send_error(404)

    def proxy_request(self):
        try:
            content_length = self.headers.get('Content-Length')
            body = None
            if content_length:
                body = self.rfile.read(int(content_length))

            url = f"{BACKEND_URL}{self.path}"
            req = urllib.request.Request(url, data=body, method=self.command)

            for header, value in self.headers.items():
                if header.lower() not in ('host', 'connection'):
                    req.add_header(header, value)

            req.add_header('X-Forwarded-For', self.client_address[0])

            try:
                response = urllib.request.urlopen(req)
                self.send_response(response.status)
                for header, value in response.headers.items():
                    self.send_header(header, value)
                self.end_headers()
                self.wfile.write(response.read())
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, f"Bad Gateway: {e}")

    def serve_static(self):
        if self.path == '/' or self.path == '':
            self.path = '/index.html'

        file_path = FRONTEND_DIR / self.path.lstrip('/')

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            self.send_response(200)
            if self.path.endswith('.html'):
                self.send_header('Content-Type', 'text/html')
            elif self.path.endswith('.json'):
                self.send_header('Content-Type', 'application/json')
            elif self.path.endswith('.css'):
                self.send_header('Content-Type', 'text/css')
            elif self.path.endswith('.js'):
                self.send_header('Content-Type', 'application/javascript')
            else:
                self.send_header('Content-Type', 'application/octet-stream')

            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))

if __name__ == '__main__':
    PORT = 8888
    Handler = ProxyHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Frontend proxy running on http://localhost:{PORT}")
        print(f"Backend: {BACKEND_URL}")
        print(f"Frontend dir: {FRONTEND_DIR}")
        httpd.serve_forever()
