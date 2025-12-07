"""Certificate distribution service."""
import base64
import re
from typing import List

from app.core.logging_config import logger
from app.models.distribution_result import DistributionResult
from app.models.student_model import Student
from app.services.excel_parser import ExcelParser
from app.utils.text_utils import clean_number
from app.utils.zip_utils import ZipUtils


class Distributor:
    """Service for distributing certificates to students."""
    
    # Pattern to match student ID in filename (7-9 digits)
    ID_PATTERN = re.compile(r'\d{7,9}')
    
    def __init__(self):
        """Initialize distributor."""
        self.excel_parser = ExcelParser()
        self.zip_utils = ZipUtils()
    
    def process(self, excel_bytes: bytes, zip_bytes: bytes) -> List[DistributionResult]:
        """
        Process Excel and ZIP files to match certificates with students.
        
        Args:
            excel_bytes: Excel file content as bytes
            zip_bytes: ZIP file containing PDF certificates
            
        Returns:
            List of DistributionResult objects
        """
        logger.info("Starting certificate distribution process")
        
        # Parse Excel to get students
        try:
            students = self.excel_parser.parse_students(excel_bytes)
        except Exception as e:
            logger.error(f"Failed to parse Excel: {e}")
            raise ValueError(f"Excel parsing failed: {e}")
        
        # Extract ZIP files
        try:
            zip_files = self.zip_utils.extract_zip(zip_bytes)
        except Exception as e:
            logger.error(f"Failed to extract ZIP: {e}")
            raise ValueError(f"ZIP extraction failed: {e}")
        
        # Build ID -> PDF mapping from ZIP filenames
        id_to_pdf = {}
        for filename, pdf_bytes in zip_files.items():
            if not filename.lower().endswith('.pdf'):
                continue
            
            match = self.ID_PATTERN.search(filename)
            if match:
                student_id = match.group(0)
                id_to_pdf[student_id] = pdf_bytes
                logger.debug(f"Matched PDF {filename} to ID {student_id}")
        
        logger.info(f"Found {len(id_to_pdf)} certificates in ZIP")
        
        # Match students with certificates
        results = []
        for student in students:
            try:
                result = self._match_student(student, id_to_pdf)
                results.append(result)
            except Exception as e:
                logger.warning(f"Error processing student {student.field1}: {e}")
                results.append(DistributionResult(
                    id=student.field2 or "",
                    email=student.email or "",
                    status="processing_error"
                ))
        
        ready_count = sum(1 for r in results if r.status == "ready_to_send")
        missing_count = sum(1 for r in results if r.status == "missing_certificate")
        logger.info(f"Distribution complete: {ready_count} ready, {missing_count} missing")
        
        return results
    
    def _match_student(self, student: Student, id_to_pdf: dict[str, bytes]) -> DistributionResult:
        """
        Match a student with their certificate.
        
        Args:
            student: Student object
            id_to_pdf: Dictionary mapping student ID to PDF bytes
            
        Returns:
            DistributionResult object
        """
        student_id = student.field2
        
        if not student_id:
            return DistributionResult(
                id="",
                email=student.email or "",
                status="invalid_id"
            )
        
        # Clean ID to match format
        cleaned_id = clean_number(student_id)
        if not cleaned_id:
            return DistributionResult(
                id=student_id,
                email=student.email or "",
                status="invalid_id"
            )
        
        # Find matching PDF
        pdf_bytes = id_to_pdf.get(cleaned_id)
        
        if not pdf_bytes:
            return DistributionResult(
                id=cleaned_id,
                email=student.email or "",
                status="missing_certificate"
            )
        
        # Encode PDF to Base64
        try:
            file_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            filename = f"תעודת סיום {cleaned_id}.pdf"
            
            return DistributionResult(
                id=cleaned_id,
                email=student.email or "",
                filename=filename,
                file_base64=file_b64,
                status="ready_to_send"
            )
        except Exception as e:
            logger.warning(f"Base64 encoding failed for student {cleaned_id}: {e}")
            return DistributionResult(
                id=cleaned_id,
                email=student.email or "",
                status="encoding_error"
            )

