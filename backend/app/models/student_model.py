"""Student data model."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class Student(BaseModel):
    """Student model with normalized fields."""
    
    field1: Optional[str] = Field(None, description="Student name")
    field2: Optional[str] = Field(None, description="Student ID (ת.ז)")
    field3: Optional[str] = Field(None, description="Additional field")
    
    # Additional fields that might come from Excel
    email: Optional[str] = Field(None, description="Student email")
    
    class Config:
        extra = "allow"  # Allow additional fields from Excel
    
    @field_validator('field2', mode='before')
    @classmethod
    def clean_id(cls, v: Any) -> Optional[str]:
        """Clean ID field - remove non-digits."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return str(int(v))
        text = str(v).strip()
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, text))
        return cleaned if cleaned else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for certificate generation."""
        return {
            "field1": self.field1,
            "field2": self.field2,
            "field3": self.field3,
        }

