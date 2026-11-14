
import base64
import io
import requests
from PIL import Image, ImageDraw

# Create a synthetic test image
image = Image.new("RGB", (640, 480), "white")
draw = ImageDraw.Draw(image)
draw.ellipse((250, 150, 390, 290), fill="gray")
draw.rectangle((180, 210, 460, 300), fill="lightgray")

buffer = io.BytesIO()
image.save(buffer, format="JPEG")

image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

# Send image to RodeOS DLC API
payload = {
    "frame_id": "frame_001",
    "timestamp": 0.0,
    "image_base64": image_base64,
    "individual_index": 0
}

response = requests.post(
    "http://127.0.0.1:8001/v1/analyze-frame",
    json=payload,
    timeout=30
)

print("HTTP status:", response.status_code)
print("Response:")
print(response.text)
