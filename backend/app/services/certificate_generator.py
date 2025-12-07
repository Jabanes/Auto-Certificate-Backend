"""Certificate generation service."""
import io
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.core.config import settings
from app.core.logging_config import logger
from app.models.student_model import Student
from app.utils.file_utils import get_template_path, load_fields_config, template_exists
from app.utils.text_utils import reshape_rtl_text


class CertificateGenerator:
    """Service for generating certificate PDFs."""
    
    def __init__(self):
        """Initialize certificate generator."""
        self._fields_config = None
    
    def _get_fields_config(self) -> Dict[str, Any]:
        """Get fields configuration (cached)."""
        if self._fields_config is None:
            self._fields_config = load_fields_config()
        return self._fields_config
    
    def create_single(self, student: Student) -> bytes:
        """
        Create a single certificate PDF for a student.
        
        Args:
            student: Student object with field data
            
        Returns:
            PDF bytes
            
        Raises:
            FileNotFoundError: If template doesn't exist
            ValueError: If PDF generation fails
        """
        logger.info(f"Generating certificate for student: {student.field1} (ID: {student.field2})")
        
        if not template_exists():
            logger.error(f"Template file not found: {get_template_path()}")
            raise FileNotFoundError(f"Template file not found: {get_template_path()}")
        
        try:
            img = Image.open(get_template_path()).convert("RGBA")
        except Exception as e:
            logger.error(f"Failed to open template: {e}")
            raise ValueError(f"Failed to load template image: {e}")
        
        draw = ImageDraw.Draw(img)
        fields_config = self._get_fields_config()
        student_dict = student.to_dict()
        
        # Render each field
        for key, value in student_dict.items():
            if key not in fields_config or not value:
                continue
            
            try:
                self._render_field(draw, img, key, value, fields_config[key])
            except Exception as e:
                logger.warning(f"Failed to render field {key}: {e}")
                continue
        
        # Convert to PDF
        try:
            img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PDF")
            buf.seek(0)
            pdf_bytes = buf.read()
            logger.info(f"Certificate generated successfully ({len(pdf_bytes)} bytes)")
            return pdf_bytes
        except Exception as e:
            logger.error(f"Failed to convert image to PDF: {e}")
            raise ValueError(f"PDF generation failed: {e}")
    
    def create_batch(self, students: List[Student]) -> List[tuple[str, bytes]]:
        """
        Create certificates for multiple students.
        
        Args:
            students: List of Student objects
            
        Returns:
            List of tuples (filename, pdf_bytes)
        """
        logger.info(f"Generating batch of {len(students)} certificates")
        
        results = []
        successful = 0
        failed = 0
        
        for student in students:
            try:
                pdf_bytes = self.create_single(student)
                
                # Generate filename
                field1 = str(student.field1 or "").strip()
                field2 = str(student.field2 or "").strip()
                filename = f'certificate-{field1}-{field2}.pdf'
                filename = filename.replace(" ", "_")
                
                results.append((filename, pdf_bytes))
                successful += 1
                
            except Exception as e:
                logger.error(f"Failed to generate certificate for student {student.field1}: {e}")
                failed += 1
                continue
        
        logger.info(f"Batch generation complete: {successful} successful, {failed} failed")
        return results
    
    def _render_field(
        self,
        draw: ImageDraw.Draw,
        img: Image.Image,
        field_key: str,
        value: str,
        cfg: Dict[str, Any]
    ):
        """Render a single field on the certificate."""
        text = str(value) if value else ""
        
        # Special handling for field2 (ID)
        if field_key == "field2" and text:
            text = "ת.ז: " + text
        
        if not text:
            return
        
        # Reshape RTL text
        bidi_text = reshape_rtl_text(text)
        
        # Get font with binary search sizing
        font = self._fit_font_to_box(draw, bidi_text, cfg)
        
        # Get position
        x, y = cfg["pos"]
        
        # Handle alignment
        if cfg.get("align") in ("center", "right"):
            bbox = draw.textbbox((0, 0), bidi_text, font=font)
            w = bbox[2] - bbox[0]
            if cfg["align"] == "center":
                x -= w // 2
            elif cfg["align"] == "right":
                x -= w
        
        # Apply glow effect if enabled
        glow_cfg = cfg.get("glow")
        if glow_cfg and glow_cfg.get("enabled", False):
            self._apply_glow(img, draw, x, y, bidi_text, font, glow_cfg)
        
        # Draw text
        draw.text((x, y), bidi_text, font=font, fill=cfg["fill"])
    
    def _fit_font_to_box(self, draw: ImageDraw.Draw, text: str, cfg: Dict[str, Any]) -> ImageFont.FreeTypeFont:
        """Binary search for optimal font size."""
        max_font_size = cfg.get("font_size", 24)
        min_font_size = cfg.get("min_font_size", 12)
        font_file = cfg["font"]
        
        box_width = cfg.get("box_width")
        if not box_width:
            return self._load_font(font_file, max_font_size, cfg.get("bold", False), cfg.get("italic", False))
        
        margins = cfg.get("margins", {})
        left_margin = margins.get("left", 0)
        right_margin = margins.get("right", 0)
        effective_width = box_width - left_margin - right_margin
        
        if effective_width <= 0:
            return self._load_font(font_file, min_font_size, cfg.get("bold", False), cfg.get("italic", False))
        
        low, high = min_font_size, max_font_size
        best_font = None
        
        while low <= high:
            mid = (low + high) // 2
            font = self._load_font(font_file, mid, cfg.get("bold", False), cfg.get("italic", False))
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= effective_width:
                best_font = font
                low = mid + 1
            else:
                high = mid - 1
        
        return best_font or self._load_font(font_file, min_font_size, cfg.get("bold", False), cfg.get("italic", False))
    
    def _load_font(self, font_file: str, size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
        """Load font with graceful fallback."""
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
                font_path_local = Path(settings.FONTS_DIR) / fname
                if font_path_local.exists():
                    return ImageFont.truetype(str(font_path_local), size)
            except (IOError, OSError):
                pass
            
            try:
                return ImageFont.truetype(fname, size)
            except (IOError, OSError):
                continue
        
        logger.warning(f"Font '{font_file}' not found, falling back to default font")
        return ImageFont.load_default()
    
    def _apply_glow(
        self,
        img: Image.Image,
        draw: ImageDraw.Draw,
        x: int,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        glow_cfg: Dict[str, Any]
    ):
        """Apply glow effect to text."""
        try:
            radius = glow_cfg.get("radius", 5)
            if radius <= 0:
                return
            
            glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)
            glow_draw.text((x, y), text, font=font, fill=glow_cfg.get("color", "#000000"))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius))
            
            opacity = glow_cfg.get("opacity", 0.5)
            if opacity < 1.0:
                alpha = glow_layer.getchannel('A')
                alpha = alpha.point(lambda i: i * opacity)
                glow_layer.putalpha(alpha)
            
            img = Image.alpha_composite(img, glow_layer)
            draw = ImageDraw.Draw(img)
        except Exception as e:
            logger.warning(f"Glow effect failed: {e}")

