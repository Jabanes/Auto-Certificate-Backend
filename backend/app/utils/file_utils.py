"""File handling utilities."""
import io
import json
from pathlib import Path
from typing import Dict, Any

from PIL import Image

from app.core.config import settings
from app.core.logging_config import logger


def ensure_data_directory() -> Path:
    """Ensure data directory exists."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings.DATA_DIR


def load_fields_config() -> Dict[str, Any]:
    """
    Load fields configuration from JSON file with default glow settings.
    
    Returns:
        Dictionary of field configurations
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    config_path = Path(settings.FIELDS_CONFIG_PATH)
    
    if not config_path.exists():
        logger.error(f"Fields config file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in fields config: {e}")
        raise
    
    # Set default glow settings for fields that don't have them
    default_glow = {
        "enabled": False,
        "color": "#000000",
        "opacity": 0.4,
        "radius": 6
    }
    
    for field in config.values():
        if "glow" not in field:
            field["glow"] = default_glow.copy()
    
    logger.info(f"Loaded fields config from {config_path} with {len(config)} fields")
    return config


def save_template_image(image_bytes: bytes) -> Path:
    """
    Save template image to disk.
    
    Args:
        image_bytes: Image file bytes
        
    Returns:
        Path to saved template file
        
    Raises:
        ValueError: If image is invalid or too large
    """
    if len(image_bytes) > settings.MAX_TEMPLATE_SIZE:
        raise ValueError(f"Template too large (max {settings.MAX_TEMPLATE_SIZE} bytes)")
    
    # Validate image
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception as e:
        logger.error(f"Invalid image file: {e}")
        raise ValueError(f"Invalid or corrupted image file: {e}")
    
    # Save template
    ensure_data_directory()
    template_path = Path(settings.TEMPLATE_PATH)
    
    try:
        # Reopen image (verify() closes it)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        temp_path = template_path.with_suffix('.tmp.png')
        img.save(temp_path, format="PNG")
        
        # Atomic replace
        temp_path.replace(template_path)
        logger.info(f"Template saved successfully to {template_path}")
        return template_path
    except Exception as e:
        logger.error(f"Failed to save template: {e}")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        raise


def get_template_path() -> Path:
    """Get path to template image."""
    return Path(settings.TEMPLATE_PATH)


def template_exists() -> bool:
    """Check if template file exists."""
    return Path(settings.TEMPLATE_PATH).exists()

