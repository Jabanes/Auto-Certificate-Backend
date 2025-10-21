from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io, zipfile, os, json
import arabic_reshaper
from bidi.algorithm import get_display
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import io, os
from fastapi.middleware.cors import CORSMiddleware
import zipfile
import io, os, base64, pandas as pd, zipfile
from fastapi import HTTPException

app = FastAPI()

# Allow requests from your GitHub Pages site
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jabanes.github.io", 
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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

        
        
        text = str(value)
        if key == "field2":
            text = "ת.ז: " + text
            
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        font = fit_font_to_box(draw, bidi_text, cfg)

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


def fit_font_to_box(draw, text: str, cfg: Dict[str, Any]) -> ImageFont.FreeTypeFont:
    """
    Dynamically adjust font size so text fits within the field's box width,
    respecting optional margins.
    """
    max_font_size = cfg.get("font_size", 24)
    min_font_size = cfg.get("min_font_size", 12)
    font_file = cfg["font"]

    # Base box width
    box_width = cfg.get("box_width")
    if not box_width:
        return _load_font(font_file, max_font_size, cfg.get("bold", False), cfg.get("italic", False))

    # Apply margins if provided
    margins = cfg.get("margins", {})
    left_margin = margins.get("left", 0)
    right_margin = margins.get("right", 0)
    effective_width = box_width - left_margin - right_margin

    font_size = max_font_size
    while font_size >= min_font_size:
        font = _load_font(font_file, font_size, cfg.get("bold", False), cfg.get("italic", False))
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= effective_width:
            return font  # ✅ Found a fitting font size

        font_size -= 2

    return _load_font(font_file, min_font_size, cfg.get("bold", False), cfg.get("italic", False))



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

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Deployment test successful!"}

# ----------- Template management endpoints -----------

@app.get("/template")
def get_template():
    """
    Returns the current certificate template as an image file for preview.
    Uses FileResponse instead of StreamingResponse to avoid 'closed file' issues.
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail="Template file not found")

    return FileResponse(
        path=TEMPLATE_PATH,
        media_type="image/png",
        filename=os.path.basename(TEMPLATE_PATH)
    )


@app.post("/template")
async def upload_new_template(file: UploadFile = File(...)):
    """
    Upload a new certificate template (PNG or JPG) and replace the old one.
    The file name stays the same (certificate-template.png).
    """
    allowed_types = ["image/png", "image/jpeg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG or JPG files are allowed")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Validate image can actually be opened
    try:
        img = Image.open(io.BytesIO(contents))
        img.verify()  # Just validates integrity, doesn’t load pixels
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

    # Normalize to PNG (convert JPG to PNG)
    img = Image.open(io.BytesIO(contents)).convert("RGBA")
    temp_path = TEMPLATE_PATH + ".tmp"
    img.save(temp_path, format="PNG")

    # Replace old file
    os.replace(temp_path, TEMPLATE_PATH)

    return {"status": "success", "message": "Template updated successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, 
        reload_dirs=["."]
    )


@app.post("/distribute-certificates")
async def distribute_certificates(
    excel: UploadFile = File(...),
    zip_file: UploadFile = File(...),
):
    """
    Matches certificates (ZIP of PDFs) to students using ID numbers.
    Excel file can contain any number of columns — only 'ID' and 'Email' are required,
    detected automatically (supports Hebrew or English column names).
    Example PDF filenames: '301112345_אדר.pdf' or '301112345.pdf'
    """

    import io, os, base64, pandas as pd, zipfile, re
    from fastapi import HTTPException

    # --- Validate Excel file ---
    if not excel.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Excel file must be .xlsx or .xls")

    # --- Validate ZIP file ---
    if not zip_file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Must upload a ZIP file of certificates")

    # --- Read Excel ---
    excel_bytes = await excel.read()
    try:
        df = pd.read_excel(io.BytesIO(excel_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading Excel file: {e}")

    # --- Normalize column names ---
    normalized_cols = {str(c).strip().lower(): c for c in df.columns}
    lowered = list(normalized_cols.keys())

    # --- Try to detect ID column (Hebrew or English) ---
    id_col_key = next(
        (
            c
            for c in lowered
            if re.search(r"(id|ת.?ז|תעודת.?זהות)", c)
        ),
        None,
    )

    # --- Try to detect Email column (Hebrew or English) ---
    email_col_key = next(
        (
            c
            for c in lowered
            if re.search(r"(mail|אימ.?ייל|דוא.?ל|email)", c)
        ),
        None,
    )

    if not id_col_key or not email_col_key:
        raise HTTPException(
            status_code=400,
            detail="Excel must include columns for ID (ת.ז) and Email (אימייל)"
        )

    id_col = normalized_cols[id_col_key]
    email_col = normalized_cols[email_col_key]

    # --- Read ZIP and extract IDs from filenames ---
    zip_bytes = await zip_file.read()
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
            id_to_pdf = {}
            for filename in z.namelist():
                if not filename.lower().endswith(".pdf"):
                    continue
                # Extract 7–9 digit ID from filename
                match = re.search(r"\d{7,9}", filename)
                if match:
                    student_id = match.group(0)
                    id_to_pdf[student_id] = z.read(filename)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupted ZIP file")

    # --- Build response ---
    results = []
    for _, row in df.iterrows():
        raw_id = str(row[id_col]).strip()
        # Remove non-digit chars (like spaces or formatting)
        student_id = re.sub(r"\D", "", raw_id)
        email = str(row[email_col]).strip()
        pdf_bytes = id_to_pdf.get(student_id)

        if pdf_bytes:
            file_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            results.append({
                "id": student_id,
                "email": email,
                "filename": f"תעודת סיום {student_id}.pdf",
                "file_base64": file_b64,
                "status": "ready_to_send"
            })
        else:
            results.append({
                "id": student_id,
                "email": email,
                "status": "missing_certificate"
            })

    return {"students": results}
