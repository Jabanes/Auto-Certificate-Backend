"""Batch request models."""
from typing import List, Optional

from pydantic import BaseModel, Field


class BatchRequest(BaseModel):
    """Request model for batch certificate generation."""
    
    students: List[dict] = Field(..., description="List of student data dictionaries")
    zip_name: Optional[str] = Field("certificates.zip", description="Name for the output ZIP file")
    
    class Config:
        json_schema_extra = {
            "example": {
                "students": [
                    {"field1": "John Doe", "field2": "123456789", "field3": "Course Name"}
                ],
                "zip_name": "certificates.zip"
            }
        }


class ExcelUploadRequest(BaseModel):
    """Request model for Excel upload and certificate generation."""
    
    admin_email: Optional[str] = Field(None, description="Admin email to receive ZIP file")
    zip_name: Optional[str] = Field("certificates.zip", description="Name for the output ZIP file")

