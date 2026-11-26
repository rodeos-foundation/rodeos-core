import json
import time
import urllib.request

API_URL = "http://127.0.0.1:8001"

def step_once(marker_name: str, delta_cm: list[float]):
    payload = json.dumps({
        "marker": marker_name,
        "delta_location_cm": delta_cm,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}/markers",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        return json.loads(resp.read().decode("utf-8"))

if __name__ == "__main__":
    for _ in range(3):
        print(step_once("Nose", [0.0, 0.0, 0.5]))
        time.sleep(0.5)