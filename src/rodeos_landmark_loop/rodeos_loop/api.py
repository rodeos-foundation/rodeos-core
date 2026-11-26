import json
import urllib.request
from pathlib import Path
from threading import Lock
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .config import load_config, resolve_path
from .vision import analyze_images, image_info, VisionError
from .optimizer import aggregate_landmark_errors, propose_marker_corrections

app = FastAPI(title="RodeOS Landmark Analysis API", version="0.1.0")
CFG = load_config()
UNREAL_BRIDGE_URL = "http://127.0.0.1:8002"

STATE_LOCK = Lock()
MARKER_OFFSETS: dict[str, list[float]] = {
    "Nose": [0.0, 0.0, 0.0],
}
PENDING_COMMANDS: list[dict] = []
RESET_PENDING = False

class AnalyzeRequest(BaseModel):
    image_paths: list[str]
    # Optional 2D positions of visible Unreal marker centers in each image.
    # Example: {"rat_000.png":{"Nose":{"x":760,"y":330}}}
    marker_observations: dict = {}

class MarkerUpdate(BaseModel):
    marker: str
    delta_location_cm: list[float] = Field(default=[0.0, 0.0, 0.0], min_length=3, max_length=3)

@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "rodeos-landmark-analysis",
        "dlc_enabled": bool(CFG["deeplabcut"].get("enabled", False)),
        "config": str(resolve_path(CFG, CFG["deeplabcut"]["config_path"]))
    }

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        images = [Path(p) for p in req.image_paths]
        for p in images:
            if not p.exists():
                raise FileNotFoundError(f"Image not found: {p}")
        predictions = analyze_images(images, CFG)
        errors = aggregate_landmark_errors(predictions, req.marker_observations, CFG)
        proposals = propose_marker_corrections(errors, CFG)
        return {
            "predictions": predictions,
            "errors": errors,
            "correction_proposals": proposals,
            "note": "2D residuals are not directly converted to 3D offsets."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/image-info")
def get_image_info(path: str):
    try:
        return image_info(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/poll")
def poll_commands():
    global RESET_PENDING
    with STATE_LOCK:
        cmds = list(PENDING_COMMANDS)
        PENDING_COMMANDS.clear()
        reset_flag = RESET_PENDING
        RESET_PENDING = False
    return {
        "reset": reset_flag,
        "commands": cmds,
    }

@app.post("/markers/reset")
def reset_markers():
    global RESET_PENDING
    with STATE_LOCK:
        for k in MARKER_OFFSETS:
            MARKER_OFFSETS[k] = [0.0, 0.0, 0.0]
        PENDING_COMMANDS.clear()
        RESET_PENDING = True
    return {"ok": True, "markers": MARKER_OFFSETS}

@app.get("/markers")
def get_markers():
    try:
        with urllib.request.urlopen(f"{UNREAL_BRIDGE_URL}/markers", timeout=0.5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        with STATE_LOCK:
            return {
                name: {"display_offset_cm": list(off)}
                for name, off in MARKER_OFFSETS.items()
            }

@app.post("/markers")
def update_marker(cmd: MarkerUpdate):
    with STATE_LOCK:
        cur = MARKER_OFFSETS.setdefault(cmd.marker, [0.0, 0.0, 0.0])
        new_offset = [
            round(cur[0] + float(cmd.delta_location_cm[0]), 6),
            round(cur[1] + float(cmd.delta_location_cm[1]), 6),
            round(cur[2] + float(cmd.delta_location_cm[2]), 6),
        ]
        MARKER_OFFSETS[cmd.marker] = new_offset
        PENDING_COMMANDS.append({
            "landmark": cmd.marker,
            "offset_cm": new_offset,
        })
        snapshot = {
            name: {"display_offset_cm": list(off)}
            for name, off in MARKER_OFFSETS.items()
        }

    try:
        payload = json.dumps([cmd.model_dump()]).encode("utf-8")
        req = urllib.request.Request(
            f"{UNREAL_BRIDGE_URL}/markers",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            bridge_resp = json.loads(resp.read().decode("utf-8"))
        return {"ok": True, "markers": snapshot, "bridge": bridge_resp}
    except Exception:
        return {"ok": True, "markers": snapshot, "bridge": None}