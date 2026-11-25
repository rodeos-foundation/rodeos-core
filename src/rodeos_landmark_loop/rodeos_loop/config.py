from pathlib import Path
import yaml

def load_config(path="config.yaml"):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p.resolve()}")
    with p.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_config_dir"] = str(p.resolve().parent)
    return cfg

def resolve_path(cfg, value):
    p = Path(value)
    if p.is_absolute():
        return p
    return Path(cfg["_config_dir"]) / p
