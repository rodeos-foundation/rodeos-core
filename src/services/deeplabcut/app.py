
import base64
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import yaml
from PIL import Image
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SERVICE_NAME = "RodeOS DeepLabCut Service"

MODE = os.getenv("RODEOS_DLC_MODE", "mock").lower()
DLC_CONFIG = os.getenv("DLC_CONFIG", "")

DLC_DEVICE = os.getenv("DLC_DEVICE", "cuda")
DLC_SHUFFLE = int(os.getenv("DLC_SHUFFLE", "1"))
DLC_TRAININGSETINDEX = int(
    os.getenv("DLC_TRAININGSETINDEX", "0")
)

MAX_IMAGE_BYTES = 15 * 1024 * 1024

# DeepLabCut inference is serialized to avoid simultaneous
# model access from multiple HTTP requests.
inference_lock = threading.Lock()

app = FastAPI(
    title=SERVICE_NAME,
    version="0.2.0",
    description="Pose inference service for RodeOS and Unreal Engine",
)


# ---------------------------------------------------------
# API schemas
# ---------------------------------------------------------

class AnalyzeFrameRequest(BaseModel):
    frame_id: str = "frame-001"
    timestamp: float = 0.0

    # Base64-encoded JPEG or PNG image
    image_base64: str

    # Which animal to return, when multiple are detected
    individual_index: int = Field(default=0, ge=0)


class Keypoint(BaseModel):
    name: str
    x: float
    y: float
    confidence: float
    individual_index: int


class AnalyzeFrameResponse(BaseModel):
    frame_id: str
    timestamp: float

    source: str
    image_width: int
    image_height: int

    individual_index: int
    keypoints: list[Keypoint]


# ---------------------------------------------------------
# Image utilities
# ---------------------------------------------------------

def decode_image(image_base64: str) -> bytes:
    """Decode and validate a base64 image."""

        # Accept both raw base64 and data:image/...;base64...
    if "," in image_base64 and image_base64.startswith("data:"):
        image_base64 = image_base64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(
            image_base64,
            validate=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid base64 image",
        ) from exc

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty image",
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds 15 MB limit",
        )

    return image_bytes


def get_image_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """Read image dimensions without retaining the image."""

    try:
        with Image.open(
            __import__("io").BytesIO(image_bytes)
        ) as image:
            image.verify()

        with Image.open(
            __import__("io").BytesIO(image_bytes)
        ) as image:
            return image.size

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unsupported or corrupted image",
        ) from exc


# ---------------------------------------------------------
# Mock inference
# ---------------------------------------------------------

MOCK_BODYPARTS = [
    "nose",
    "left_ear",
    "right_ear",
    "neck",
    "mid_back",
    "tail_base",
    "tail_mid",
    "tail_tip",
]


def run_mock_inference(
    width: int,
    height: int,
    individual_index: int,
) -> list[Keypoint]:
    """
    Return deterministic example keypoints.

    These coordinates are illustrative only.
    They are NOT biological measurements or model predictions.
    """

    normalized_points = [
        (0.72, 0.28),
        (0.79, 0.20),
        (0.80, 0.35),
        (0.61, 0.34),
        (0.43, 0.46),
        (0.25, 0.58),
        (0.15, 0.68),
        (0.07, 0.78),
    ]

    keypoints = []

    for name, (nx, ny) in zip(
        MOCK_BODYPARTS,
        normalized_points,
    ):
        keypoints.append(
            Keypoint(
                name=name,
                x=round(nx * width, 2),
                y=round(ny * height, 2),
                confidence=0.99,
                individual_index=individual_index,
            )
        )

    return keypoints


# ---------------------------------------------------------
# DeepLabCut configuration and inference
# ---------------------------------------------------------

def load_bodypart_names(config_path: str) -> list[str]:
    """Read bodypart names from the DLC project config."""

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config.get("bodyparts", [])


def run_deeplabcut_inference(
    image_bytes: bytes,
    individual_index: int,
) -> list[Keypoint]:

    if not DLC_CONFIG:
        raise RuntimeError(
            "DLC_CONFIG environment variable is not configured"
        )

    config_path = Path(DLC_CONFIG)

    if not config_path.is_file():
        raise RuntimeError(
            f"DeepLabCut config not found: {config_path}"
        )

    # Import DLC only when real inference is requested.
    import deeplabcut

    bodypart_names = load_bodypart_names(str(config_path))

    with tempfile.TemporaryDirectory(
        prefix="rodeos_dlc_"
    ) as temp_dir:

        temp_path = Path(temp_dir)
        image_path = temp_path / "input.jpg"

        image_path.write_bytes(image_bytes)

        with inference_lock:

            predictions = deeplabcut.analyze_images(
                config=str(config_path),
                images=str(image_path),
                destfolder=str(temp_path),
                shuffle=DLC_SHUFFLE,
                trainingsetindex=DLC_TRAININGSETINDEX,
                device=DLC_DEVICE,
                save_as_csv=False,
                plotting=False,
            )

        if not predictions:
            raise RuntimeError(
                "DeepLabCut returned no predictions"
            )

        # DLC 3.0.2 maps image filenames to prediction dictionaries.
        prediction = predictions.get(str(image_path))

        if prediction is None:
            # Fallback for versions returning a normalized path.
            prediction = next(iter(predictions.values()))

        if "bodyparts" not in prediction:
            raise RuntimeError(
                "DeepLabCut result does not contain 'bodyparts'"
            )

        bodyparts = np.asarray(prediction["bodyparts"])

        # Expected:
        # [individuals, bodyparts, (x, y, confidence)]
        #
        # Also support:
        # [bodyparts, (x, y, confidence)]

        if bodyparts.ndim == 2:
            bodyparts = bodyparts[np.newaxis, ...]

        if bodyparts.ndim != 3 or bodyparts.shape[-1] < 3:
            raise RuntimeError(
                f"Unexpected bodyparts array shape: {bodyparts.shape}"
            )

        if individual_index >= bodyparts.shape[0]:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Individual {individual_index} not found. "
                    f"Detected individuals: {bodyparts.shape[0]}"
                ),
            )

        selected_individual = bodyparts[individual_index]

        keypoints = []

        for index, point in enumerate(selected_individual):

            name = (
                bodypart_names[index]
                if index < len(bodypart_names)
                else f"bodypart_{index}"
            )

            x, y, confidence = point[:3]

            keypoints.append(
                Keypoint(
                    name=name,
                    x=float(x),
                    y=float(y),
                    confidence=float(confidence),
                    individual_index=individual_index,
                )
            )

        return keypoints


# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------

@app.get("/health")
def health():

    return {
        "service": SERVICE_NAME,
        "status": "running",
        "mode": MODE,
        "dlc_configured": bool(DLC_CONFIG),
        "dlc_config_exists": (
            Path(DLC_CONFIG).is_file()
            if DLC_CONFIG
            else False
        ),
    }


# ---------------------------------------------------------
# Frame analysis endpoint
# ---------------------------------------------------------

@app.post(
    "/v1/analyze-frame",
    response_model=AnalyzeFrameResponse,
)
async def analyze_frame(request: AnalyzeFrameRequest):

    image_bytes = decode_image(request.image_base64)

    width, height = get_image_dimensions(image_bytes)

    try:

        if MODE == "mock":

            keypoints = run_mock_inference(
                width,
                height,
                request.individual_index,
            )

            source = "mock"

        elif MODE == "deeplabcut":

            keypoints = await run_in_threadpool(
                run_deeplabcut_inference,
                image_bytes,
                request.individual_index,
            )

            source = "deeplabcut"

        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unsupported inference mode: {MODE}",
            )

        return AnalyzeFrameResponse(
            frame_id=request.frame_id,
            timestamp=request.timestamp,
            source=source,
            image_width=width,
            image_height=height,
            individual_index=request.individual_index,
            keypoints=keypoints,
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
