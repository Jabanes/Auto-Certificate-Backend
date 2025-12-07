import base64
import io
import json
import logging
import os
import re
import zipfile
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import arabic_reshaper
import pandas as pd
from bidi.algorithm import get_display
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://jabanes.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "certificate-template.png")
FIELDS_CONFIG_PATH = os.getenv("FIELDS_CONFIG", "fields_config.json")
FONTS_DIR = "fonts"
MAX_TEMPLATE_SIZE = 10 * 1024 * 1024
ILLEGAL_FILENAME_CHARS = r'[\\/*?:"<>|]'


class BatchRequest(BaseModel):
    students: List[Dict[str, Any]]
    zipName: Optional[str] = "certificates.zip"


def sanitize_filename(filename: str) -> str:
    """Remove illegal filesystem characters from filename."""
    sanitized = re.sub(ILLEGAL_FILENAME_CHARS, '_', filename)
    sanitized = sanitized.strip('. ')
    return sanitized or "certificate"


def reshape_rtl_text(text: str) -> str:
    """Centralized RTL text reshaping with fallback."""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception as e:
        logger.warning(f"RTL reshaping failed for text '{text[:50]}...': {e}")
        return text


def load_fields_config(path: str) -> Dict[str, Dict[str, Any]]:
    """Load fields configuration from JSON file with default glow settings."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"Fields config file not found: {path}")
        raise HTTPException(status_code=500, detail=f"Configuration file not found: {path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in fields config: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid configuration file format: {e}")

    default_glow = {
        "enabled": False,
        "color": "#000000",
        "opacity": 0.4,
        "radius": 6
    }

    for field in config.values():
        if "glow" not in field:
            field["glow"] = default_glow.copy()

    logger.info(f"Loaded fields config from {path} with {len(config)} fields")
    return config


@lru_cache(maxsize=1)
def get_fields_config_cached() -> Dict[str, Dict[str, Any]]:
    """Cached fields config loader. Clear cache on file change or restart."""
    return load_fields_config(FIELDS_CONFIG_PATH)


def get_fields_config() -> Dict[str, Dict[str, Any]]:
    """Get fields config with cache invalidation support."""
    try:
        return get_fields_config_cached()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading fields config: {e}")
        get_fields_config_cached.cache_clear()
        raise HTTPException(status_code=500, detail="Failed to load configuration")


def force_reload_config():
    """Force reload of fields config by clearing cache."""
    get_fields_config_cached.cache_clear()
    logger.info("Fields config cache cleared")


def load_font(font_file: str, size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    """Load font with graceful fallback. Prioritizes fonts/ directory."""
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
            font_path_local = os.path.join(FONTS_DIR, fname)
            if os.path.exists(font_path_local):
                return ImageFont.truetype(font_path_local, size)
        except (IOError, OSError):
            pass

        try:
            return ImageFont.truetype(fname, size)
        except (IOError, OSError):
            continue

    logger.warning(f"Font '{font_file}' not found, falling back to default font")
    return ImageFont.load_default()


def fit_font_to_box_binary_search(draw: ImageDraw.Draw, text: str, cfg: Dict[str, Any]) -> ImageFont.FreeTypeFont:
    """Binary search for optimal font size. O(log N) complexity."""
    max_font_size = cfg.get("font_size", 24)
    min_font_size = cfg.get("min_font_size", 12)
    font_file = cfg["font"]

    box_width = cfg.get("box_width")
    if not box_width:
        return load_font(font_file, max_font_size, cfg.get("bold", False), cfg.get("italic", False))

    margins = cfg.get("margins", {})
    left_margin = margins.get("left", 0)
    right_margin = margins.get("right", 0)
    effective_width = box_width - left_margin - right_margin

    if effective_width <= 0:
        return load_font(font_file, min_font_size, cfg.get("bold", False), cfg.get("italic", False))

    low, high = min_font_size, max_font_size
    best_font = None

    while low <= high:
        mid = (low + high) // 2
        font = load_font(font_file, mid, cfg.get("bold", False), cfg.get("italic", False))
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= effective_width:
            best_font = font
            low = mid + 1
        else:
            high = mid - 1

    return best_font or load_font(font_file, min_font_size, cfg.get("bold", False), cfg.get("italic", False))


def render_pdf_for_student(stu: Dict[str, Any], fields_config: Dict[str, Dict[str, Any]]) -> bytes:
    """Render a single certificate to PDF bytes with robust error handling."""
    try:
        if not os.path.exists(TEMPLATE_PATH):
            raise HTTPException(status_code=500, detail=f"Template file not found: {TEMPLATE_PATH}")

        img = Image.open(TEMPLATE_PATH).convert("RGBA")
    except IOError as e:
        logger.error(f"Failed to open template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load template image: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading template: {e}")
        raise HTTPException(status_code=500, detail=f"Template loading error: {e}")

    draw = ImageDraw.Draw(img)

    for key, value in stu.items():
        if key not in fields_config:
            continue

        cfg = fields_config[key]

        try:
            text = str(value) if value is not None else ""
            if key == "field2" and text:
                text = "ת.ז: " + text

            if not text:
                continue

            bidi_text = reshape_rtl_text(text)
            font = fit_font_to_box_binary_search(draw, bidi_text, cfg)

            x, y = cfg["pos"]

            if cfg.get("align") in ("center", "right"):
                bbox = draw.textbbox((0, 0), bidi_text, font=font)
                w = bbox[2] - bbox[0]
                if cfg["align"] == "center":
                    x -= w // 2
                elif cfg["align"] == "right":
                    x -= w

            glow_cfg = cfg.get("glow")
            if glow_cfg and glow_cfg.get("enabled", False):
                radius = glow_cfg.get("radius", 5)
                if radius > 0:
                    try:
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
                    except Exception as e:
                        logger.warning(f"Glow effect failed for field {key}: {e}")

            draw.text((x, y), bidi_text, font=font, fill=cfg["fill"])

        except Exception as e:
            logger.warning(f"Failed to render field {key}: {e}")
            continue

    try:
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PDF")
        buf.seek(0)
        return buf.read()
    except Exception as e:
        logger.error(f"Failed to convert image to PDF: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


def build_zip(files: List[Tuple[str, bytes]]) -> bytes:
    """Build ZIP file with error handling."""
    out = io.BytesIO()
    try:
        with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for filename, content in files:
                sanitized_name = sanitize_filename(filename)
                zf.writestr(sanitized_name, content)
        out.seek(0)
        return out.read()
    except Exception as e:
        logger.error(f"ZIP creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP file: {e}")


@app.post("/generate-certificate")
def generate_certificate(data: Dict[str, Any]):
    """Generate a single certificate."""
    try:
        fields_config = get_fields_config()
        pdf_bytes = render_pdf_for_student(data, fields_config)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="certificate.pdf"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Certificate generation error: {e}")


@app.post("/generate-certificates-batch")
def generate_certificates_batch(payload: BatchRequest):
    """Generate certificates in batch with per-student error handling."""
    fields_config = get_fields_config()
    files: List[Tuple[str, bytes]] = []
    processed = 0
    failed = 0

    for idx, stu in enumerate(payload.students):
        try:
            pdf_bytes = render_pdf_for_student(stu, fields_config)
            field1 = str(stu.get("field1", "")).strip()
            field2 = str(stu.get("field2", "")).strip()
            fname = f'certificate-{field1}-{field2}.pdf'
            files.append((fname, pdf_bytes))
            processed += 1
        except HTTPException:
            failed += 1
            logger.error(f"Failed to generate certificate for student {idx + 1}")
            continue
        except Exception as e:
            failed += 1
            logger.error(f"Unexpected error generating certificate for student {idx + 1}: {e}")
            continue

    if not files:
        raise HTTPException(status_code=400, detail="No certificates could be generated")

    try:
        zip_bytes = build_zip(files)
        zip_name = sanitize_filename(payload.zipName or "certificates.zip")
        logger.info(f"Batch generation complete: {processed} processed, {failed} failed")
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch ZIP creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create batch ZIP: {e}")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Deployment test successful!"}


@app.get("/template")
def get_template():
    """Return the current certificate template as an image file."""
    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail="Template file not found")

    return FileResponse(
        path=TEMPLATE_PATH,
        media_type="image/png",
        filename=os.path.basename(TEMPLATE_PATH)
    )


@app.head("/template")
def head_template():
    """Handle HEAD requests for the template."""
    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=404)
    return {}


@app.post("/template")
async def upload_new_template(file: UploadFile = File(...)):
    """Upload a new certificate template (PNG or JPG)."""
    allowed_types = ["image/png", "image/jpeg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG or JPG files are allowed")

    try:
        contents = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    if len(contents) > MAX_TEMPLATE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        img = Image.open(io.BytesIO(contents))
        img.verify()
    except Exception as e:
        logger.error(f"Invalid image file: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid or corrupted image file: {e}")

    try:
        img = Image.open(io.BytesIO(contents)).convert("RGBA")
        temp_path = TEMPLATE_PATH + ".tmp"
        img.save(temp_path, format="PNG")
        os.replace(temp_path, TEMPLATE_PATH)
        force_reload_config()
        logger.info("Template updated successfully")
        return {"status": "success", "message": "Template updated successfully"}
    except Exception as e:
        logger.error(f"Failed to save template: {e}")
        if os.path.exists(TEMPLATE_PATH + ".tmp"):
            try:
                os.remove(TEMPLATE_PATH + ".tmp")
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to save template: {e}")


@app.post("/distribute-certificates")
async def distribute_certificates(
    excel: UploadFile = File(...),
    zip_file: UploadFile = File(...),
):
    """Match certificates (ZIP of PDFs) to students using ID numbers."""
    if not excel.filename or not excel.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Excel file must be .xlsx or .xls")

    if not zip_file.filename or not zip_file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Must upload a ZIP file of certificates")

    try:
        excel_bytes = await excel.read()
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {e}")

    try:
        df = pd.read_excel(io.BytesIO(excel_bytes))
    except Exception as e:
        logger.error(f"Error parsing Excel file: {e}")
        raise HTTPException(status_code=400, detail=f"Error reading Excel file: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Excel file is empty")

    normalized_cols = {str(c).strip().lower(): c for c in df.columns}
    lowered = list(normalized_cols.keys())

    id_patterns = [
        r"id",
        r"ת.?ז",
        r"תעודת.?זהות",
        r"מספר.?זהות"
    ]

    email_patterns = [
        r"mail",
        r"אימ.?ייל",
        r"דוא.?ל",
        r"email"
    ]

    id_col_key = None
    for pattern in id_patterns:
        id_col_key = next((c for c in lowered if re.search(pattern, c, re.IGNORECASE)), None)
        if id_col_key:
            break

    email_col_key = None
    for pattern in email_patterns:
        email_col_key = next((c for c in lowered if re.search(pattern, c, re.IGNORECASE)), None)
        if email_col_key:
            break

    if not id_col_key or not email_col_key:
        raise HTTPException(
            status_code=400,
            detail="Excel must include columns for ID (ת.ז) and Email (אימייל)"
        )

    id_col = normalized_cols[id_col_key]
    email_col = normalized_cols[email_col_key]

    try:
        zip_bytes = await zip_file.read()
    except Exception as e:
        logger.error(f"Failed to read ZIP file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read ZIP file: {e}")

    id_to_pdf = {}
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
            for filename in z.namelist():
                if not filename.lower().endswith(".pdf"):
                    continue
                match = re.search(r"\d{7,9}", filename)
                if match:
                    student_id = match.group(0)
                    try:
                        id_to_pdf[student_id] = z.read(filename)
                    except Exception as e:
                        logger.warning(f"Failed to read PDF {filename} from ZIP: {e}")
                        continue
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid or corrupted ZIP file")
    except Exception as e:
        logger.error(f"Error processing ZIP file: {e}")
        raise HTTPException(status_code=400, detail=f"ZIP processing error: {e}")

    results = []
    for idx, row in df.iterrows():
        try:
            raw_id = str(row[id_col]).strip()
            student_id = re.sub(r"\D", "", raw_id)
            email = str(row[email_col]).strip()

            if not student_id:
                results.append({
                    "id": "",
                    "email": email,
                    "status": "invalid_id"
                })
                continue

            pdf_bytes = id_to_pdf.get(student_id)

            if pdf_bytes:
                try:
                    file_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
                    results.append({
                        "id": student_id,
                        "email": email,
                        "filename": f"תעודת סיום {student_id}.pdf",
                        "file_base64": file_b64,
                        "status": "ready_to_send"
                    })
                except Exception as e:
                    logger.warning(f"Base64 encoding failed for student {student_id}: {e}")
                    results.append({
                        "id": student_id,
                        "email": email,
                        "status": "encoding_error"
                    })
            else:
                results.append({
                    "id": student_id,
                    "email": email,
                    "status": "missing_certificate"
                })
        except Exception as e:
            logger.warning(f"Error processing row {idx}: {e}")
            results.append({
                "id": "",
                "email": "",
                "status": "processing_error"
            })

    logger.info(f"Distributed certificates: {len([r for r in results if r['status'] == 'ready_to_send'])} ready, {len([r for r in results if r['status'] == 'missing_certificate'])} missing")
    return {"students": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["."]
    )
