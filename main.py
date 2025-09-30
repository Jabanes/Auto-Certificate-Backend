from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont
import io

app = FastAPI()

class CertificateData(BaseModel):
    firstName: str
    lastName: str
    grade: int

@app.post("/generate-certificate")
def generate_certificate(data: CertificateData):
    # Load template
    template = Image.open("certificate-template.png").convert("RGB")
    draw = ImageDraw.Draw(template)

    # --- Configuration for each field ---
    config = {
        "firstName": {
            "pos": (210, 200),
            "font": "arial.ttf",   # change to your font file
            "size": 48,
            "fill": "black",
        },
        "lastName": {
            "pos": (310, 300),
            "font": "arialbd.ttf",  # bold font
            "size": 30,
            "fill": "black",
        },
        "grade": {
            "pos": (160, 300),
            "font": "arial.ttf",
            "size": 30,
            "fill": "red",  # grade in red, just as example
        },
    }

    # Draw each field
    for field, value in {
        "firstName": data.firstName,
        "lastName": data.lastName,
        "grade": str(data.grade),
    }.items():
        cfg = config[field]
        font = ImageFont.truetype(cfg["font"], cfg["size"])
        draw.text(cfg["pos"], value, font=font, fill=cfg["fill"])

    # Save to bytes
    img_bytes = io.BytesIO()
    template.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return StreamingResponse(img_bytes, media_type="image/png")
