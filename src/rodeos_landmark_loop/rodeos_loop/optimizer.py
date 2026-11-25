from collections import defaultdict
import math

def aggregate_landmark_errors(predictions, marker_observations, cfg):
    """
    marker_observations format:
      {image_name: {bodypart: {"x": px, "y": px}}}
    predictions format:
      {image_name: {bodypart: {"x","y","likelihood"}}}

    Computes per-bodypart image-space residuals across views.
    """
    pcut = float(cfg["optimization"]["min_confidence"])
    sums = defaultdict(lambda: {"dx": 0.0, "dy": 0.0, "n": 0, "confidence": 0.0})
    for image_name, bodyparts in predictions.items():
        observed = marker_observations.get(image_name, {})
        for bp, pred in bodyparts.items():
            if bp not in observed:
                continue
            conf = float(pred.get("likelihood", 0.0))
            if conf < pcut:
                continue
            dx = float(pred["x"]) - float(observed[bp]["x"])
            dy = float(pred["y"]) - float(observed[bp]["y"])
            sums[bp]["dx"] += dx
            sums[bp]["dy"] += dy
            sums[bp]["n"] += 1
            sums[bp]["confidence"] += conf

    out = {}
    for bp, v in sums.items():
        if v["n"] == 0:
            continue
        out[bp] = {
            "mean_dx_px": v["dx"] / v["n"],
            "mean_dy_px": v["dy"] / v["n"],
            "views": v["n"],
            "mean_confidence": v["confidence"] / v["n"],
        }
    return out

def propose_marker_corrections(errors, cfg):
    """
    Produces bounded image-space correction proposals.
    IMPORTANT: This is diagnostic only. Pixel errors cannot be converted to
    3D marker offsets without camera calibration/depth or multi-view triangulation.
    """
    deadband = float(cfg["optimization"]["deadband_px"])
    max_step = float(cfg["optimization"]["max_step_cm"])
    min_views = int(cfg["optimization"]["min_views"])
    proposals = {}
    for bp, e in errors.items():
        if e["views"] < min_views:
            continue
        dx, dy = e["mean_dx_px"], e["mean_dy_px"]
        mag = math.hypot(dx, dy)
        if mag <= deadband:
            continue
        # Deliberately do not guess a 3D direction from 2D pixels.
        proposals[bp] = {
            "image_error_px": [dx, dy],
            "views": e["views"],
            "mean_confidence": e["mean_confidence"],
            "requires_3d_solver": True,
            "max_allowed_step_cm": max_step,
            "reason": "Need calibrated multi-view geometry to solve a 3D correction."
        }
    return proposals
