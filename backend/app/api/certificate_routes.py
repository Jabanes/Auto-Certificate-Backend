"""Certificate generation API routes."""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from io import BytesIO

import io

from app.core.logging_config import logger
from app.models.batch_request import BatchRequest, ExcelUploadRequest
from app.models.student_model import Student
from app.services.certificate_generator import CertificateGenerator
from app.services.email_service import EmailService
from app.services.excel_parser import ExcelParser
from app.utils.zip_utils import ZipUtils

router = APIRouter(prefix="", tags=["certificates"])

# Service instances
excel_parser = ExcelParser()
certificate_generator = CertificateGenerator()
zip_utils = ZipUtils()
email_service = EmailService()


@router.post("/upload-excel-and-generate")
async def upload_excel_and_generate(
    excel: UploadFile = File(...),
    admin_email: str = Form(None),
    zip_name: str = Form("certificates.zip")
):
    """
    Upload Excel file, generate certificates, and optionally email ZIP to admin.
    
    This endpoint replaces the N8N workflow:
    Excel → Student Mapping → ZIP Generation → Email Admin
    
    Args:
        excel: Excel file with student data
        admin_email: Optional admin email to receive ZIP file
        zip_name: Name for the output ZIP file
        
    Returns:
        ZIP file with generated certificates
    """
    logger.info(f"Excel upload and generate request received: {excel.filename}")
    
    # Validate Excel file
    if not excel.filename or not excel.filename.endswith((".xlsx", ".xls")):
        logger.warning(f"Invalid file type: {excel.filename}")
        raise HTTPException(
            status_code=400,
            detail="Excel file must be .xlsx or .xls"
        )
    
    # Read Excel file
    try:
        excel_bytes = await excel.read()
        logger.info(f"Excel file read: {len(excel_bytes)} bytes")
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {e}")
    
    # Parse students from Excel
    try:
        students = excel_parser.parse_students(excel_bytes)
        logger.info(f"Parsed {len(students)} students from Excel")
    except ValueError as e:
        logger.error(f"Excel parsing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error parsing Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Excel parsing error: {e}")
    
    if not students:
        raise HTTPException(status_code=400, detail="No students found in Excel file")
    
    # Generate certificates
    try:
        certificate_files = certificate_generator.create_batch(students)
        logger.info(f"Generated {len(certificate_files)} certificates")
    except Exception as e:
        logger.error(f"Certificate generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Certificate generation failed: {e}")
    
    if not certificate_files:
        raise HTTPException(
            status_code=500,
            detail="No certificates could be generated"
        )
    
    # Build ZIP file
    try:
        zip_bytes = zip_utils.build_zip(certificate_files)
        logger.info(f"ZIP file created: {len(zip_bytes)} bytes")
    except ValueError as e:
        logger.error(f"ZIP creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Send email to admin if provided
    if admin_email:
        try:
            email_service.send_zip_to_admin(admin_email, zip_bytes, zip_name)
            logger.info(f"ZIP file sent to admin: {admin_email}")
        except Exception as e:
            logger.warning(f"Failed to send email to admin: {e}")
            # Don't fail the request if email fails
    
    # Return ZIP file
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'}
    )


@router.post("/generate-certificates-batch")
def generate_certificates_batch(payload: BatchRequest):
    """
    Flow A: Generate certificates from JSON payload and email ZIP to admin.
    
    Purpose:
    - Receives students JSON
    - Generates PDF files
    - Creates ZIP
    - Emails ZIP ONLY to ADMIN_RESULTS_EMAIL
    
    Args:
        payload: BatchRequest with list of students
        
    Returns:
        JSON success response
    """
    logger.info(f"Flow A - Batch generation request received: {len(payload.students)} students")
    
    # Convert dicts to Student objects
    students = []
    for student_dict in payload.students:
        try:
            student = Student(**student_dict)
            students.append(student)
            logger.debug(f"Parsed student: {student.field1} (ID: {student.field2})")
        except Exception as e:
            logger.warning(f"Invalid student data: {e}")
            continue
    
    if not students:
        logger.error("No valid students provided")
        raise HTTPException(status_code=400, detail="No valid students provided")
    
    logger.info(f"Parsed {len(students)} students from JSON")
    
    # Generate certificates
    try:
        certificate_files = certificate_generator.create_batch(students)
        logger.info(f"Generated {len(certificate_files)} certificates")
    except Exception as e:
        logger.error(f"Certificate generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Certificate generation failed: {e}")
    
    if not certificate_files:
        logger.error("No certificates could be generated")
        raise HTTPException(
            status_code=500,
            detail="No certificates could be generated"
        )
    
    # Build ZIP file
    try:
        zip_bytes = zip_utils.build_zip(certificate_files)
        logger.info(f"ZIP file created: {len(zip_bytes)} bytes")
    except ValueError as e:
        logger.error(f"ZIP creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    zip_name = payload.zip_name or "certificates.zip"
    
    # Send ZIP to admin email
    logger.info("Sending ZIP to admin email...")
    try:
        success = email_service.send_admin_zip(zip_bytes, zip_name)
        if success:
            logger.info("ZIP file sent successfully to admin")
        else:
            logger.error("Failed to send ZIP to admin")
    except Exception as e:
        logger.error(f"Error sending ZIP to admin: {e}")
        # Don't fail the request, but log the error
    
    # Return JSON success response
    return {
        "status": "success",
        "message": "Certificates generated and ZIP sent to admin",
        "students_processed": len(students),
        "certificates_generated": len(certificate_files),
        "zip_size_bytes": len(zip_bytes),
        "zip_filename": zip_name
    }


@router.post("/generate-certificates-excel")
async def generate_certificates_excel(
    excel: UploadFile = File(...),
    zip_name: str = Form("certificates.zip")
):
    """
    Generate certificates from Excel file, email ZIP to admin, and return ZIP as download.
    
    Purpose:
    - Receives Excel file with student data
    - Parses Excel to extract students
    - Generates PDF files for each student
    - Creates ZIP file
    - Emails ZIP to ADMIN_RESULTS_EMAIL
    - Returns ZIP file as HTTP download
    
    Args:
        excel: Excel file (.xlsx or .xls) with student data
        zip_name: Optional name for the ZIP file (default: "certificates.zip")
        
    Returns:
        ZIP file download (application/zip)
    """
    logger.info(f"Excel file received: {excel.filename}")
    
    # Validate Excel file
    if not excel.filename or not excel.filename.endswith((".xlsx", ".xls")):
        logger.warning(f"Invalid file type: {excel.filename}")
        raise HTTPException(
            status_code=400,
            detail="Excel file must be .xlsx or .xls"
        )
    
    # Read Excel file
    try:
        excel_bytes = await excel.read()
        logger.info(f"Excel file read: {len(excel_bytes)} bytes")
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {e}")
    
    # Parse students from Excel
    try:
        students = excel_parser.parse_students(excel_bytes)
        logger.info(f"Parsed {len(students)} students from Excel")
    except ValueError as e:
        logger.error(f"Excel parsing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error parsing Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Excel parsing error: {e}")
    
    if not students:
        logger.error("No valid students found in Excel file")
        raise HTTPException(status_code=400, detail="No valid students found in Excel file")
    
    # Generate certificates
    try:
        certificate_files = certificate_generator.create_batch(students)
        logger.info(f"Generated {len(certificate_files)} certificates")
    except FileNotFoundError as e:
        logger.error(f"Template file not found: {e}")
        raise HTTPException(status_code=500, detail=f"Template file not found: {e}")
    except Exception as e:
        logger.error(f"Certificate generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Certificate generation failed: {e}")
    
    if not certificate_files:
        logger.error("No certificates could be generated")
        raise HTTPException(
            status_code=500,
            detail="No certificates could be generated"
        )
    
    # Build ZIP file
    try:
        zip_bytes = zip_utils.build_zip(certificate_files)
        logger.info(f"ZIP created successfully: {len(zip_bytes)} bytes")
    except ValueError as e:
        logger.error(f"ZIP creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating ZIP: {e}")
        raise HTTPException(status_code=500, detail=f"ZIP creation error: {e}")
    
    # Send ZIP to admin email
    logger.info("Sending ZIP to admin email...")
    try:
        success = email_service.send_admin_zip(zip_bytes, zip_name)
        if success:
            logger.info("Done sending ZIP to admin")
        else:
            logger.error("Failed to send ZIP to admin (check SMTP configuration)")
    except Exception as e:
        logger.error(f"Error sending ZIP to admin: {e}")
        # Don't fail the request, but log the error
    
    # Return ZIP file as download
    logger.info(f"Returning ZIP file download: {zip_name} ({len(zip_bytes)} bytes)")
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_name}"}
    )


@router.post("/generate-certificates-excel-dev")
async def generate_certificates_excel_dev(
    excel: UploadFile = File(...),
    zip_name: str = Form("certificates.zip")
):
    """
    DEV ENDPOINT: Generate certificates from Excel file and return ZIP as download (NO EMAIL).
    
    Purpose:
    - Receives Excel file with student data
    - Parses Excel to extract students
    - Generates PDF files for each student
    - Creates ZIP file
    - Returns ZIP file as HTTP download (NO EMAIL SENT)
    
    Args:
        excel: Excel file (.xlsx or .xls) with student data
        zip_name: Optional name for the ZIP file (default: "certificates.zip")
        
    Returns:
        ZIP file download (application/zip)
    """
    logger.info(f"[DEV] Excel file received: {excel.filename}")
    
    # Validate Excel file
    if not excel.filename or not excel.filename.endswith((".xlsx", ".xls")):
        logger.warning(f"Invalid file type: {excel.filename}")
        raise HTTPException(
            status_code=400,
            detail="Excel file must be .xlsx or .xls"
        )
    
    # Read Excel file
    try:
        excel_bytes = await excel.read()
        logger.info(f"[DEV] Excel file read: {len(excel_bytes)} bytes")
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {e}")
    
    # Parse students from Excel
    try:
        students = excel_parser.parse_students(excel_bytes)
        logger.info(f"[DEV] Parsed {len(students)} students from Excel")
    except ValueError as e:
        logger.error(f"Excel parsing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error parsing Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Excel parsing error: {e}")
    
    if not students:
        logger.error("No valid students found in Excel file")
        raise HTTPException(status_code=400, detail="No valid students found in Excel file")
    
    # Generate certificates
    try:
        certificate_files = certificate_generator.create_batch(students)
        logger.info(f"[DEV] Generated {len(certificate_files)} certificates")
    except FileNotFoundError as e:
        logger.error(f"Template file not found: {e}")
        raise HTTPException(status_code=500, detail=f"Template file not found: {e}")
    except Exception as e:
        logger.error(f"Certificate generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Certificate generation failed: {e}")
    
    if not certificate_files:
        logger.error("No certificates could be generated")
        raise HTTPException(
            status_code=500,
            detail="No certificates could be generated"
        )
    
    # Build ZIP file
    try:
        zip_bytes = zip_utils.build_zip(certificate_files)
        logger.info(f"[DEV] ZIP created successfully: {len(zip_bytes)} bytes")
    except ValueError as e:
        logger.error(f"ZIP creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating ZIP: {e}")
        raise HTTPException(status_code=500, detail=f"ZIP creation error: {e}")
    
    # DEV ENDPOINT: Skip email sending, return ZIP directly
    logger.info(f"[DEV] Returning ZIP file download: {zip_name} ({len(zip_bytes)} bytes)")
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_name}"}
    )


@router.post("/generate-certificate")
def generate_certificate(data: dict):
    """
    Generate a single certificate (legacy endpoint).
    
    Args:
        data: Dictionary with student field data
        
    Returns:
        PDF file
    """
    logger.info("Single certificate generation request received")
    
    try:
        student = Student(**data)
    except Exception as e:
        logger.error(f"Invalid student data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid student data: {e}")
    
    try:
        pdf_bytes = certificate_generator.create_single(student)
    except Exception as e:
        logger.error(f"Certificate generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Certificate generation failed: {e}")
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="certificate.pdf"'}
    )

