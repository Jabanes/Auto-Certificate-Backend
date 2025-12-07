"""Excel parsing service."""
import io
import re
from typing import List, Optional

import pandas as pd

from app.core.logging_config import logger
from app.models.student_model import Student
from app.utils.text_utils import clean_number, normalize_column_name


class ExcelParser:
    """Service for parsing Excel files and extracting student data."""
    
    # Hebrew column name mappings
    HEBREW_COLUMN_MAPPINGS = {
        "שם": "field1",
        "ת.ז": "field2",
        "תז": "field2",
        "מספר": "field2",
        "מספר זהות": "field2",
        "תעודת זהות": "field2",
        "אימייל": "email",
        "דואל": "email",
        "email": "email",
    }
    
    # Column name patterns for matching
    ID_PATTERNS = [
        r"id",
        r"ת.?ז",
        r"תעודת.?זהות",
        r"מספר.?זהות",
        r"field2",
    ]
    
    EMAIL_PATTERNS = [
        r"mail",
        r"אימ.?ייל",
        r"דוא.?ל",
        r"email",
    ]
    
    NAME_PATTERNS = [
        r"name",
        r"שם",
        r"field1",
    ]
    
    FIELD3_PATTERNS = [
        r"field3",
        r"מספר.?תעודה",
        r"מספר.?תעודת.?סיום",
        r"serial",
        r"certificate.?number",
        r"cert.?number",
        r"מספר",
    ]
    
    @classmethod
    def parse_students(cls, file_bytes: bytes) -> List[Student]:
        """
        Parse Excel file and extract student data.
        
        Args:
            file_bytes: Excel file content as bytes
            
        Returns:
            List of Student objects
            
        Raises:
            ValueError: If Excel file is invalid or cannot be parsed
        """
        logger.info("Starting Excel parsing")
        
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception as e:
            logger.error(f"Error parsing Excel file: {e}")
            raise ValueError(f"Error reading Excel file: {e}")
        
        if df.empty:
            logger.warning("Excel file is empty")
            raise ValueError("Excel file is empty")
        
        logger.info(f"Excel file loaded: {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Normalize column names
        normalized_cols = {}
        for col in df.columns:
            normalized = normalize_column_name(str(col))
            normalized_cols[normalized] = col
        
        # Find field columns using patterns
        field1_col = cls._find_column(df, normalized_cols, cls.NAME_PATTERNS)
        field2_col = cls._find_column(df, normalized_cols, cls.ID_PATTERNS)
        field3_col = cls._find_column(df, normalized_cols, cls.FIELD3_PATTERNS)  # Search for field3
        email_col = cls._find_column(df, normalized_cols, cls.EMAIL_PATTERNS)
        
        # Also check direct Hebrew mappings
        for orig_col in df.columns:
            col_lower = str(orig_col).strip().lower()
            if col_lower in cls.HEBREW_COLUMN_MAPPINGS:
                mapped = cls.HEBREW_COLUMN_MAPPINGS[col_lower]
                if mapped == "field1" and not field1_col:
                    field1_col = orig_col
                elif mapped == "field2" and not field2_col:
                    field2_col = orig_col
                elif mapped == "email" and not email_col:
                    email_col = orig_col
        
        logger.info(f"Detected columns - field1: {field1_col}, field2: {field2_col}, field3: {field3_col}, email: {email_col}")
        
        # Parse students
        students = []
        for idx, row in df.iterrows():
            try:
                student_data = {}
                
                if field1_col:
                    student_data["field1"] = cls._safe_get(row, field1_col)
                
                if field2_col:
                    raw_id = cls._safe_get(row, field2_col)
                    student_data["field2"] = clean_number(raw_id)
                
                if field3_col:
                    raw_field3 = cls._safe_get(row, field3_col)
                    # Clean field3 value - convert to string and strip whitespace
                    if raw_field3:
                        student_data["field3"] = str(raw_field3).strip()
                    else:
                        student_data["field3"] = None
                
                if email_col:
                    student_data["email"] = cls._safe_get(row, email_col)
                
                # Create student object (will validate)
                student = Student(**student_data)
                students.append(student)
                
            except Exception as e:
                logger.warning(f"Error parsing row {idx + 1}: {e}")
                continue
        
        logger.info(f"Parsed {len(students)} students from Excel")
        return students
    
    @staticmethod
    def _find_column(df: pd.DataFrame, normalized_cols: dict, patterns: List[str]) -> Optional[str]:
        """Find column matching patterns."""
        for pattern in patterns:
            for normalized, original in normalized_cols.items():
                if re.search(pattern, normalized, re.IGNORECASE):
                    return original
        return None
    
    @staticmethod
    def _safe_get(row: pd.Series, col: str) -> Optional[str]:
        """Safely get value from row, handling NaN."""
        try:
            value = row[col]
            if pd.isna(value):
                return None
            return str(value).strip() if value else None
        except (KeyError, AttributeError):
            return None

