"""ZIP file utilities."""
import io
import zipfile
from typing import List, Tuple

from app.core.logging_config import logger
from app.utils.text_utils import sanitize_filename


class ZipUtils:
    """Utility class for ZIP file operations."""
    
    @staticmethod
    def build_zip(files: List[Tuple[str, bytes]]) -> bytes:
        """
        Build ZIP file from list of (filename, content) tuples.
        
        Args:
            files: List of tuples (filename, bytes)
            
        Returns:
            ZIP file as bytes
            
        Raises:
            ValueError: If files list is empty or ZIP creation fails
        """
        if not files:
            raise ValueError("Cannot create ZIP from empty file list")
        
        out = io.BytesIO()
        
        try:
            with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for filename, content in files:
                    sanitized_name = sanitize_filename(filename)
                    zf.writestr(sanitized_name, content)
                    logger.debug(f"Added {sanitized_name} to ZIP")
            
            out.seek(0)
            zip_bytes = out.read()
            logger.info(f"Created ZIP file with {len(files)} files ({len(zip_bytes)} bytes)")
            return zip_bytes
            
        except Exception as e:
            logger.error(f"ZIP creation failed: {e}")
            raise ValueError(f"Failed to create ZIP file: {e}")
    
    @staticmethod
    def extract_zip(zip_bytes: bytes) -> dict[str, bytes]:
        """
        Extract ZIP file and return dictionary of filename -> content.
        
        Args:
            zip_bytes: ZIP file as bytes
            
        Returns:
            Dictionary mapping filename to file bytes
            
        Raises:
            ValueError: If ZIP is invalid or corrupted
        """
        files = {}
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                for filename in zf.namelist():
                    try:
                        content = zf.read(filename)
                        files[filename] = content
                        logger.debug(f"Extracted {filename} from ZIP")
                    except Exception as e:
                        logger.warning(f"Failed to read {filename} from ZIP: {e}")
                        continue
            
            logger.info(f"Extracted {len(files)} files from ZIP")
            return files
            
        except zipfile.BadZipFile:
            logger.error("Invalid or corrupted ZIP file")
            raise ValueError("Invalid or corrupted ZIP file")
        except Exception as e:
            logger.error(f"Error processing ZIP file: {e}")
            raise ValueError(f"ZIP processing error: {e}")

