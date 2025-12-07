"""Text processing utilities."""
import re
from typing import Any, Optional

import arabic_reshaper
from bidi.algorithm import get_display

from app.core.logging_config import logger


def reshape_rtl_text(text: str) -> str:
    """
    Centralized RTL text reshaping with fallback.
    
    Args:
        text: Text to reshape (may contain Hebrew/Arabic)
        
    Returns:
        Properly reshaped and displayed RTL text
    """
    if not text:
        return text
    
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception as e:
        logger.warning(f"RTL reshaping failed for text '{text[:50]}...': {e}")
        return str(text)


def sanitize_filename(filename: str) -> str:
    """
    Remove illegal filesystem characters from filename.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    if not filename:
        return "certificate"
    
    # Remove illegal characters
    illegal_chars = r'[\\/*?:"<>|]'
    sanitized = re.sub(illegal_chars, '_', filename)
    sanitized = sanitized.strip('. ')
    
    return sanitized or "certificate"


def normalize_column_name(col_name: str) -> str:
    """
    Normalize Excel column names for matching.
    
    Args:
        col_name: Original column name
        
    Returns:
        Normalized column name (lowercase, no spaces, underscores)
    """
    if not col_name:
        return ""
    
    # Convert to string, strip, lowercase
    normalized = str(col_name).strip().lower()
    # Replace spaces and common separators with underscores
    normalized = re.sub(r'[\s\-\.]+', '_', normalized)
    # Remove multiple underscores
    normalized = re.sub(r'_+', '_', normalized)
    # Remove leading/trailing underscores
    normalized = normalized.strip('_')
    
    return normalized


def clean_number(value: Any) -> Optional[str]:
    """
    Clean number field - extract digits only.
    
    Args:
        value: Value to clean (can be int, float, or string)
        
    Returns:
        Cleaned string with only digits, or None if empty
    """
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return str(int(value))
    
    text = str(value).strip()
    # Extract only digits
    cleaned = ''.join(filter(str.isdigit, text))
    
    return cleaned if cleaned else None

