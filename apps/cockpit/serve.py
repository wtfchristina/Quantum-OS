import os
import http.server
import socketserver

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FLAG_PATH = os.path.join(DIRECTORY, "attack.flag")

class CockpitHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path.startswith("/attack_toggle"):
            if os.path.exists(FLAG_PATH):
                os.remove(FLAG_PATH)
                state = "CLEAN"
            else:
                with open(FLAG_PATH, "w") as f:
                    f.write("ATTACK_ACTIVE\n")
                state = "ATTACK_ENGAGED"

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(f'{{"status": "{state}"}}'.encode("utf-8"))
            return

        super().do_GET()

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), CockpitHandler) as httpd:
        httpd.serve_forever()
