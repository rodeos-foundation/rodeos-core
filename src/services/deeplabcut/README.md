# RodeOS DeepLabCut FastAPI service

## Assumptions
- DeepLabCut 3.x project using the PyTorch engine.
- A trained project with a valid `config.yaml`.
- One uploaded frame per request.
- First individual is selected by default.

DeepLabCut's `analyze_images` API returns per-image predictions, including
`bodyparts` arrays containing x, y and confidence. This service adapts those
predictions to a stable RodeOS JSON schema.

## Install
Activate the Python environment in which DeepLabCut is installed, then:

```bash
pip install -r requirements.txt
```

Set `DLC_CONFIG` to your project's config.yaml. On Windows PowerShell:

```powershell
$env:DLC_CONFIG="C:/path/to/project/config.yaml"
$env:DLC_DEVICE="cuda:0"
uvicorn app:app --host 127.0.0.1 --port 8000
```

Test:

```powershell
curl http://127.0.0.1:8000/health
```

The Unreal client posts JSON to `/v1/analyze-frame`.

## Important performance note
This starter calls the public high-level `deeplabcut.analyze_images` API for
each frame. It is suitable for a functional integration test, but may reload
parts of the inference pipeline and is not a production real-time streaming
implementation. After confirming the data contract, replace `_run_dlc` with
a persistent, preloaded DLC 3.x inference runner and use WebSocket or batched
binary frames for streaming.

For TensorFlow-engine projects, this adapter must be changed: the DLC 3.x
`analyze_images` API documented here is implemented for PyTorch projects.
