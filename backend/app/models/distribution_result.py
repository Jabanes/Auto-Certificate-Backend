"""Distribution result models."""
from typing import List, Optional

from pydantic import BaseModel, Field


class DistributionResult(BaseModel):
    """Result model for certificate distribution."""
    
    id: str = Field(..., description="Student ID")
    email: str = Field(..., description="Student email")
    filename: Optional[str] = Field(None, description="Certificate filename")
    file_base64: Optional[str] = Field(None, description="Base64 encoded PDF content")
    status: str = Field(..., description="Status: ready_to_send, missing_certificate, invalid_id, encoding_error, processing_error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123456789",
                "email": "student@example.com",
                "filename": "תעודת סיום 123456789.pdf",
                "file_base64": "JVBERi0xLjQKJeLjz9MK...",
                "status": "ready_to_send"
            }
        }


class DistributionResponse(BaseModel):
    """Response model for distribution endpoint."""
    
    students: List[DistributionResult] = Field(..., description="List of distribution results")
    total: int = Field(..., description="Total number of students processed")
    ready_to_send: int = Field(..., description="Number of certificates ready to send")
    missing: int = Field(..., description="Number of missing certificates")
    errors: int = Field(..., description="Number of processing errors")

