# RodeOS Landmark Loop — first integration package

This package provides:
- FastAPI service
- DeepLabCut inference adapter for an existing DLC project
- multi-view landmark residual aggregation
- MCP viewport-capture adapter
- bounded correction proposal reporting

## Important engineering boundary

This is an executable integration foundation, not yet a fully autonomous marker optimizer.
A 2D image residual cannot safely be converted into a 3D marker translation without camera
intrinsics/extrinsics and multi-view geometry (or a known 3D target). This package therefore
does NOT move Unreal markers by guessing a 3D direction.

Also, synthetic training labels must be generated from known Unreal landmark coordinates
projected into each camera image. Do not train DLC on its own predictions as ground truth.

## Install

Use the same Python/conda environment that has the compatible DeepLabCut installation.

```cmd
cd C:\Users\zaukt\Projects\rodeos\landmark_loop
pip install -r requirements.txt
```

Set the actual AMBER `config.yaml` path in `config.yaml`.
Confirm that its bodypart names match the `landmarks[].bodypart` values.
Set `deeplabcut.enabled: true` only after checking the AMBER environment imports correctly.

## Start API

```cmd
run_api.bat
```

Check:
`http://127.0.0.1:8001/health`
Swagger:
`http://127.0.0.1:8001/docs`

## Capture test

The MCP capture tool schema varies by plugin version. Set `mcp.capture_arguments` in
config.yaml to the exact arguments required by your installed `CaptureEditorViewport`.
Then run:

```cmd
python capture_views.py
```

This initial script captures the current view. It does not rotate the camera yet; camera
motion must be added after the exact SetCameraTransform call schema is wired.

## Analyze existing images

```cmd
curl -X POST http://127.0.0.1:8001/analyze ^
  -H "Content-Type: application/json" ^
  -d "{\"image_paths\":[\"C:/path/to/capture.png\"]}"
```

## Next required integration

1. Confirm the exact DLC bodypart schema from AMBER `config.yaml`.
2. Add an Unreal ground-truth export that records each landmark's projected pixel coordinate
   for each captured view.
3. Solve a multi-view 3D correction using camera calibration and triangulation.
4. Apply only bounded `DisplayOffset` values to the marker components, never modify the
   anatomical bone reference positions.

## Why marker corrections are not applied automatically yet

The existing conversation does not contain the current C++ tracker source, exact marker
component names, or full MCP schemas for camera movement and Python execution. Writing an
automatic writer without those contracts risks moving the wrong components or corrupting
the rig. The capture adapter uses the verified MCP wrapper shape from this project; the
remaining write adapter is intentionally not fabricated.
