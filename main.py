from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import io, zipfile, os, json
import arabic_reshaper
from bidi.algorithm import get_display

app = FastAPI()

# ----------- Data models -----------

class BatchRequest(BaseModel):
    students: List[Dict[str, Any]]               # Each row from Excel → dict with field1, field2, ...
    zipName: Optional[str] = "certificates.zip"  # Output zip file name


# ----------- Template config -----------

TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "certificate-template.png")

def load_fields_config(path: str = "fields_config.json") -> Dict[str, Dict[str, Any]]:
    """
    Load fields configuration from a JSON file.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

config_file = os.getenv("FIELDS_CONFIG", "fields_config.json")
FIELDS_CONFIG = load_fields_config(config_file)
print("Loaded config from:", os.path.abspath(config_file))



def _load_font(font_file: str, size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    font_name, font_ext = os.path.splitext(font_file)
    style = ""
    if bold:
        style += "-Bold"
    if italic:
        style += "-Italic"

    font_filenames_to_try = []
    if style:
        font_filenames_to_try.append(f"{font_name}{style}.ttf")
    font_filenames_to_try.append(f"{font_name}.ttf")

    for fname in font_filenames_to_try:
        try:
            font_path_local = os.path.join("fonts", fname)
            return ImageFont.truetype(font_path_local, size)
        except IOError:
            try:
                return ImageFont.truetype(fname, size)
            except IOError:
                continue

    print(f"Warning: Font '{font_file}' (or its variants) not found. Falling back to default font.")
    return ImageFont.load_default()


def render_pdf_for_student(stu: Dict[str, Any], fields_config: Dict[str, Dict[str, Any]]) -> bytes:
    """
    Render a single certificate to PDF bytes, fully in-memory.
    """
    img = Image.open(TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)

    for key, value in stu.items():
        if key not in fields_config:
            continue

        cfg = fields_config[key]
        font = _load_font(
            cfg["font"],
            cfg.get("font_size", 24),
            bold=cfg.get("bold", False),
            italic=cfg.get("italic", False)
        )
        
        text = str(value)
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)

        x, y = cfg["pos"]

        if cfg.get("align") in ("center", "right"):
            bbox = draw.textbbox((0, 0), bidi_text, font=font)
            w = bbox[2] - bbox[0]
            if cfg["align"] == "center":
                x = x - w // 2
            elif cfg["align"] == "right":
                x = x - w

        draw.text((x, y), bidi_text, font=font, fill=cfg["fill"])

    buf = io.BytesIO()
    img.save(buf, format="PDF")
    buf.seek(0)
    return buf.read()


def build_zip(files: List[Tuple[str, bytes]]) -> bytes:
    """
    Create a ZIP (in-memory) from a list of (filename, content_bytes).
    """
    out = io.BytesIO()
    with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files:
            zf.writestr(filename, content)
    out.seek(0)
    return out.read()


# ----------- Endpoints -----------

@app.post("/generate-certificate")
def generate_certificate(data: Dict[str, Any]):
    """
    Single-student endpoint (kept for testing/backwards-compatibility).
    Uses predefined FIELDS_CONFIG for rendering.
    """
    pdf_bytes = render_pdf_for_student(data, FIELDS_CONFIG)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="certificate.pdf"'},
    )


@app.post("/generate-certificates-batch")
def generate_certificates_batch(payload: BatchRequest):
    """
    Batch endpoint:
    - Accepts JSON with a list of students (field1, field2, ...)
    - Renders a PDF per student in memory
    - Packs all PDFs into a ZIP (in memory)
    - Returns the ZIP to the caller (n8n)
    """
    files: List[Tuple[str, bytes]] = []

    for stu in payload.students:
        pdf_bytes = render_pdf_for_student(stu, FIELDS_CONFIG)
        # Default filename convention uses field1 and field2 if present
        fname = f'certificate-{stu.get("field1","")}-{stu.get("field2","")}.pdf'
        files.append((fname, pdf_bytes))

    zip_bytes = build_zip(files)
    zip_name = payload.zipName or "certificates.zip"

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )
