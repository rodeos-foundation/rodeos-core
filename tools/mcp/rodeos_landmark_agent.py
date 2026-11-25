from collections import deque
from typing import List, Optional
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_OLLAMA_MODEL = "qwen3.5:4b"

VALID_LANDMARKS = [
    "Back1_Center", "Back1_Right", "Back2", "Back3", "Back4",
    "Back5", "Back6", "Back7", "Back8", "Back9", "Back10",
    "TopOfHead", "LeftEar", "RightEye", "Nose", "RightEar",
    "RightShoulder", "LeftPalm", "RightPalm", "RightWrist",
    "RightArmpit", "RightVentrum", "RightLegFront", "RightAnkle",
    "RightLegBehind", "TailBase",
]

app = FastAPI(title="RodeOS Rat Landmark Agent Bridge")

pending_commands: deque[dict] = deque()
reset_flag: bool = False


class MarkerCommand(BaseModel):
    landmark: str
    offset_cm: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], min_length=3, max_length=3)
    rotation_deg: Optional[List[float]] = Field(default=None, min_length=3, max_length=3)
    scale_multiplier: Optional[List[float]] = Field(default=None, min_length=3, max_length=3)


class BatchCommandRequest(BaseModel):
    commands: List[MarkerCommand]
    reset: bool = False


class OllamaAgentRequest(BaseModel):
    instruction: str
    model: str = DEFAULT_OLLAMA_MODEL


@app.get("/health")
def health():
    return {
        "status": "ok",
        "queued_commands": len(pending_commands),
        "landmarks": VALID_LANDMARKS,
    }


@app.post("/command")
def enqueue_command(cmd: MarkerCommand):
    if cmd.landmark not in VALID_LANDMARKS:
        raise HTTPException(status_code=400, detail=f"Unknown landmark '{cmd.landmark}'")
    payload = cmd.model_dump(exclude_none=True)
    pending_commands.append(payload)
    return {"queued": payload}


@app.post("/commands")
def enqueue_commands(batch: BatchCommandRequest):
    global reset_flag
    if batch.reset:
        reset_flag = True
    accepted = []
    for cmd in batch.commands:
        if cmd.landmark not in VALID_LANDMARKS:
            raise HTTPException(status_code=400, detail=f"Unknown landmark '{cmd.landmark}'")
        payload = cmd.model_dump(exclude_none=True)
        pending_commands.append(payload)
        accepted.append(payload)
    return {"reset": batch.reset, "queued_count": len(accepted), "commands": accepted}


@app.post("/reset")
def reset_markers():
    global reset_flag
    pending_commands.clear()
    reset_flag = True
    return {"status": "reset_queued"}


@app.get("/poll")
def poll_commands():
    global reset_flag
    batch = []
    while pending_commands:
        batch.append(pending_commands.popleft())
    should_reset = reset_flag
    reset_flag = False
    return {"reset": should_reset, "commands": batch}


@app.post("/agent/prompt")
async def run_ollama_agent(req: OllamaAgentRequest):
    system_prompt = (
        "You control display offsets/rotations/scales for 3D cone markers on a rat skeletal mesh "
        "in Unreal Engine 5.9. Return ONLY valid JSON with key 'commands' (a list of objects).\n"
        "Each command object uses:\n"
        '  {"landmark": "<name>", "offset_cm": [x, y, z], "rotation_deg": [p, y, r], "scale_multiplier": [sx, sy, sz]}\n'
        "Only omit optional fields if unchanged. Valid landmark names:\n"
        f"{', '.join(VALID_LANDMARKS)}"
    )

    payload = {
        "model": req.model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.instruction},
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

    import json
    content = data.get("message", {}).get("content", "{}")
    parsed = json.loads(content)
    raw_cmds = parsed.get("commands", [])

    queued = []
    for item in raw_cmds:
        cmd = MarkerCommand(**item)
        if cmd.landmark in VALID_LANDMARKS:
            d = cmd.model_dump(exclude_none=True)
            pending_commands.append(d)
            queued.append(d)

    return {"model": req.model, "queued_count": len(queued), "commands": queued}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)