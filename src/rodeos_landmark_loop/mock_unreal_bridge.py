import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

INITIAL_STATE = {
    "Nose": {"location_cm": [10.0, 0.0, 5.0]},
}

LOCK = threading.Lock()
STATE = {k: {"location_cm": list(v["location_cm"])} for k, v in INITIAL_STATE.items()}


def _reset_state():
    STATE.clear()
    for k, v in INITIAL_STATE.items():
        STATE[k] = {"location_cm": list(v["location_cm"])}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/markers":
            with LOCK:
                self._send_json(200, STATE)
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/markers":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"[]"
            cmds = json.loads(raw.decode("utf-8"))
            with LOCK:
                for cmd in cmds:
                    name = cmd.get("marker")
                    delta = cmd.get("delta_location_cm", [0.0, 0.0, 0.0])
                    cur = STATE.setdefault(name, {"location_cm": [0.0, 0.0, 0.0]})["location_cm"]
                    STATE[name]["location_cm"] = [
                        cur[0] + float(delta[0]),
                        cur[1] + float(delta[1]),
                        cur[2] + float(delta[2]),
                    ]
                self._send_json(200, {"ok": True, "markers": STATE})
        elif self.path == "/reset":
            with LOCK:
                _reset_state()
                self._send_json(200, {"ok": True, "markers": STATE})
        else:
            self._send_json(404, {"error": "not found"})

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8002), Handler)
    print("Mock Unreal bridge listening on http://127.0.0.1:8002")
    server.serve_forever()