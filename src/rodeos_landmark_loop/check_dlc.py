import sys
from pathlib import Path
from rodeos_loop.config import load_config

cfg = load_config()
p = Path(cfg["deeplabcut"]["config_path"])
print("Config exists:", p.exists(), p)
try:
    import deeplabcut
    print("DeepLabCut import: OK")
    print("DeepLabCut version:", getattr(deeplabcut, "__version__", "unknown"))
except Exception as e:
    print("DeepLabCut import: FAILED")
    print(type(e).__name__ + ":", e)
    sys.exit(1)
