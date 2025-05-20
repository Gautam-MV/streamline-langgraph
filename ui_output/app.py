import http.server
import socketserver
import webbrowser
import os

PORT = 8000

def serve_ui(output_dir: str = ".", port: int = PORT):
    os.chdir(output_dir)
    handler = http.server.SimpleHTTPRequestHandler

    print(f"🚀 Serving UI at http://localhost:{port}")
    webbrowser.open(f"http://localhost:{port}/index.html")

    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    serve_ui()
