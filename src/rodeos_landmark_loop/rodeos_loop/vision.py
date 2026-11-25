from pathlib import Path
import inspect
import json
import cv2
import pandas as pd

class VisionError(RuntimeError):
    pass

def _load_dlc():
    try:
        import deeplabcut
        return deeplabcut
    except Exception as e:
        raise VisionError(
            "DeepLabCut is not importable in this Python environment. "
            "Install/use the same environment as the AMBER model."
        ) from e

def analyze_images(image_paths, cfg):
    """
    Runs the configured DLC model over a directory of PNG/JPG captures.
    Returns: {image_filename: {bodypart: {x,y,likelihood}}}
    """
    dlc_cfg = cfg["deeplabcut"]
    if not dlc_cfg.get("enabled", False):
        raise VisionError(
            "DeepLabCut is disabled in config.yaml. Set deeplabcut.enabled: true "
            "after confirming the AMBER config path and DLC environment."
        )

    config_path = Path(dlc_cfg["config_path"])
    if not config_path.exists():
        raise VisionError(f"AMBER config.yaml not found: {config_path}")

    image_paths = [Path(p) for p in image_paths]
    if not image_paths:
        return {}

    # DLC's folder-based inference writes HDF/CSV beside the images.
    # Use a dedicated inference folder to avoid mixing source captures and outputs.
    folder = image_paths[0].parent
    dlc = _load_dlc()

    fn = getattr(dlc, "analyze_time_lapse_frames", None)
    if fn is None:
        raise VisionError(
            "This DeepLabCut version does not expose analyze_time_lapse_frames. "
            "Use a compatible DLC release or adapt this one function to your version."
        )

    kwargs = {
        "config": str(config_path),
        "directory": str(folder),
        "frametype": image_paths[0].suffix,
        "shuffle": int(dlc_cfg.get("shuffle", 1)),
        "trainingsetindex": int(dlc_cfg.get("trainingsetindex", 0)),
        "save_as_csv": True,
    }
    sig = inspect.signature(fn)
    kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
    fn(**kwargs)

    # DLC output file naming can vary by version; select newest HDF in capture folder.
    h5_files = sorted(folder.glob("*.h5"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not h5_files:
        raise VisionError(f"DLC ran but produced no .h5 result in {folder}")

    df = pd.read_hdf(h5_files[0])
    if not isinstance(df.columns, pd.MultiIndex):
        raise VisionError(f"Unexpected DLC HDF columns: {df.columns}")

    # Typical DLC columns: scorer/bodyparts/coords. Support both 3- and 2-level columns.
    result = {}
    pcutoff = float(dlc_cfg.get("pcutoff", 0.6))
    for row_idx, row in df.iterrows():
        filename = Path(str(row_idx)).name
        bodyparts = {}
        cols = df.columns
        if cols.nlevels >= 4:
            bp_level = 2
            coord_level = 3
        elif cols.nlevels == 3:
            bp_level = 1
            coord_level = 2
        else:
            bp_level = 0
            coord_level = 1

        for bp in sorted(set(cols.get_level_values(bp_level))):
            def get_coord(coord):
                matches = [c for c in cols if c[bp_level] == bp and c[coord_level] == coord]
                if not matches:
                    return None
                return float(row[matches[0]])

            x, y = get_coord("x"), get_coord("y")
            likelihood = get_coord("likelihood")
            if x is None or y is None:
                continue
            if likelihood is None:
                likelihood = 1.0
            bodyparts[str(bp)] = {
                "x": x, "y": y, "likelihood": likelihood,
                "accepted": likelihood >= pcutoff
            }
        result[filename] = bodyparts
    return result

def image_info(path):
    img = cv2.imread(str(path))
    if img is None:
        raise VisionError(f"Cannot read image: {path}")
    h, w = img.shape[:2]
    return {"width": w, "height": h}
