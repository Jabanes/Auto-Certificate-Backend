"""Template management API routes."""
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging_config import logger
from app.utils.file_utils import get_template_path, save_template_image, template_exists

router = APIRouter(prefix="/template", tags=["template"])


@router.get("")
def get_template():
    """
    Get the current certificate template image.
    
    Returns:
        Template image file (PNG)
    """
    logger.info("Template GET request received")
    
    if not template_exists():
        logger.warning("Template file not found")
        raise HTTPException(status_code=404, detail="Template file not found")
    
    try:
        return FileResponse(
            path=str(get_template_path()),
            media_type="image/png",
            filename="template.png"
        )
    except Exception as e:
        logger.error(f"Failed to serve template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serve template: {e}")


@router.head("")
def head_template():
    """
    Handle HEAD requests for template.
    
    Returns:
        Empty response if template exists
    """
    if not template_exists():
        raise HTTPException(status_code=404)
    return {}


@router.post("")
async def upload_template(file: UploadFile = File(...)):
    """
    Upload a new certificate template image.
    
    Args:
        file: PNG or JPG image file
        
    Returns:
        Success message
    """
    logger.info(f"Template upload request received: {file.filename}")
    
    # Validate content type
    allowed_types = ["image/png", "image/jpeg"]
    if file.content_type not in allowed_types:
        logger.warning(f"Invalid file type: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail="Only PNG or JPG files are allowed"
        )
    
    # Read file
    try:
        contents = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")
    
    # Validate size
    if len(contents) > settings.MAX_TEMPLATE_SIZE:
        logger.warning(f"File too large: {len(contents)} bytes")
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {settings.MAX_TEMPLATE_SIZE} bytes)"
        )
    
    # Save template
    try:
        save_template_image(contents)
        logger.info("Template uploaded successfully")
        return {
            "status": "success",
            "message": "Template updated successfully"
        }
    except ValueError as e:
        logger.error(f"Invalid template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to save template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save template: {e}")

