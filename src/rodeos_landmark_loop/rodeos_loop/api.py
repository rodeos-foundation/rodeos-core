from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .config import load_config, resolve_path
from .vision import analyze_images, image_info, VisionError
from .optimizer import aggregate_landmark_errors, propose_marker_corrections

app = FastAPI(title="RodeOS Landmark Analysis API", version="0.1.0")
CFG = load_config()

class AnalyzeRequest(BaseModel):
    image_paths: list[str]
    # Optional 2D positions of visible Unreal marker centers in each image.
    # Example: {"rat_000.png":{"Nose":{"x":760,"y":330}}}
    marker_observations: dict = {}

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
