import argparse
from pathlib import Path
from datetime import datetime
from rodeos_loop.config import load_config, resolve_path
from rodeos_loop.mcp_bridge import MCPBridge

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1,
                        help="Number of captures. Camera movement is not automated in this first adapter.")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    out_dir = resolve_path(cfg, cfg["project"]["capture_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    bridge = MCPBridge(cfg)

    for i in range(args.count):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = out_dir / f"rat_{stamp}_{i:03d}.png"
        saved = bridge.capture_sync(path)
        print(f"CAPTURED: {saved}")

if __name__ == "__main__":
    main()
