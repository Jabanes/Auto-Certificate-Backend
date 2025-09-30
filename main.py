from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
    Load fields configuration from a JSON file and add default glow effect settings if missing.
    """
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    default_glow = {
        "enabled": False,
        "color": "#000000",
        "opacity": 0.4,
        "radius": 6
    }

    for field in config.values():
        if "glow" not in field:
            field["glow"] = default_glow.copy()

    return config


def get_fields_config() -> Dict[str, Dict[str, Any]]:
    """
    Always load the latest config on each request.
    """
    config_file = os.getenv("FIELDS_CONFIG", "fields_config.json")
    return load_fields_config(config_file)


# ----------- Font Loader -----------

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


# ----------- Renderer -----------

def render_pdf_for_student(stu: Dict[str, Any], fields_config: Dict[str, Dict[str, Any]]) -> bytes:
    """
    Render a single certificate to PDF bytes, fully in-memory.
    """
    img = Image.open(TEMPLATE_PATH).convert("RGBA")  # Use RGBA for transparency
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

        # --- Text alignment ---
        if cfg.get("align") in ("center", "right"):
            bbox = draw.textbbox((0, 0), bidi_text, font=font)
            w = bbox[2] - bbox[0]
            if cfg["align"] == "center":
                x -= w // 2
            elif cfg["align"] == "right":
                x -= w

        # --- Glow Effect ---
        glow_cfg = cfg.get("glow")
        if glow_cfg and glow_cfg.get("enabled", False):
            radius = glow_cfg.get("radius", 5)
            if radius > 0:
                glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow_layer)

                glow_draw.text((x, y), bidi_text, font=font, fill=glow_cfg.get("color", "#000000"))

                glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius))

                opacity = glow_cfg.get("opacity", 0.5)
                if opacity < 1.0:
                    alpha = glow_layer.getchannel('A')
                    alpha = alpha.point(lambda i: i * opacity)
                    glow_layer.putalpha(alpha)
                
                img = Image.alpha_composite(img, glow_layer)
                draw = ImageDraw.Draw(img)

        # --- Main Text ---
        draw.text((x, y), bidi_text, font=font, fill=cfg["fill"])

    img = img.convert("RGB")
    
    buf = io.BytesIO()
    img.save(buf, format="PDF")
    buf.seek(0)
    return buf.read()


# ----------- Zip Builder -----------

def build_zip(files: List[Tuple[str, bytes]]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files:
            zf.writestr(filename, content)
    out.seek(0)
    return out.read()


# ----------- Endpoints -----------

@app.post("/generate-certificate")
def generate_certificate(data: Dict[str, Any]):
    fields_config = get_fields_config()  # 🔄 Always fresh
    pdf_bytes = render_pdf_for_student(data, fields_config)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="certificate.pdf"'},
    )


@app.post("/generate-certificates-batch")
def generate_certificates_batch(payload: BatchRequest):
    fields_config = get_fields_config()  # 🔄 Always fresh
    files: List[Tuple[str, bytes]] = []

    for stu in payload.students:
        pdf_bytes = render_pdf_for_student(stu, fields_config)
        fname = f'certificate-{stu.get("field1","")}-{stu.get("field2","")}.pdf'
        files.append((fname, pdf_bytes))

    zip_bytes = build_zip(files)
    zip_name = payload.zipName or "certificates.zip"

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, 
        reload_dirs=["."]
    )
