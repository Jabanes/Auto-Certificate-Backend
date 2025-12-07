"""Certificate distribution API routes."""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.logging_config import logger
from app.models.distribution_result import DistributionResponse
from app.services.distributor import Distributor
from app.services.email_service import EmailService

router = APIRouter(prefix="", tags=["distribution"])

# Service instances
distributor = Distributor()
email_service = EmailService()


@router.post("/send-certificates")
async def send_certificates(
    excel: UploadFile = File(...),
    zip_file: UploadFile = File(...),
    send_emails: bool = Form(False)
):
    """
    Match certificates from ZIP with students from Excel and optionally send emails.
    
    This endpoint replaces the N8N workflow:
    ZIP + Excel → Match PDFs → Email Students
    
    Args:
        excel: Excel file with student data (must include ID and Email columns)
        zip_file: ZIP file containing PDF certificates
        send_emails: If True, send emails directly to students
        
    Returns:
        DistributionResponse with matching results
    """
    logger.info("Certificate distribution request received")
    
    # Validate Excel file
    if not excel.filename or not excel.filename.endswith((".xlsx", ".xls")):
        logger.warning(f"Invalid Excel file type: {excel.filename}")
        raise HTTPException(
            status_code=400,
            detail="Excel file must be .xlsx or .xls"
        )
    
    # Validate ZIP file
    if not zip_file.filename or not zip_file.filename.endswith(".zip"):
        logger.warning(f"Invalid ZIP file type: {zip_file.filename}")
        raise HTTPException(
            status_code=400,
            detail="Must upload a ZIP file of certificates"
        )
    
    # Read Excel file
    try:
        excel_bytes = await excel.read()
        logger.info(f"Excel file read: {len(excel_bytes)} bytes")
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {e}")
    
    # Read ZIP file
    try:
        zip_bytes = await zip_file.read()
        logger.info(f"ZIP file read: {len(zip_bytes)} bytes")
    except Exception as e:
        logger.error(f"Failed to read ZIP file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read ZIP file: {e}")
    
    # Process distribution
    try:
        results = distributor.process(excel_bytes, zip_bytes)
        logger.info(f"Distribution processed: {len(results)} students")
    except ValueError as e:
        logger.error(f"Distribution processing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in distribution: {e}")
        raise HTTPException(status_code=500, detail=f"Distribution processing error: {e}")
    
    # Send emails if requested
    if send_emails:
        logger.info("Sending emails to students")
        email_results = {}
        
        for result in results:
            if result.status == "ready_to_send" and result.email and result.file_base64:
                try:
                    import base64
                    pdf_bytes = base64.b64decode(result.file_base64)
                    filename = result.filename or f"certificate_{result.id}.pdf"
                    
                    success = email_service.send_certificate(
                        result.email,
                        pdf_bytes,
                        filename
                    )
                    email_results[result.email] = success
                except Exception as e:
                    logger.warning(f"Failed to send email to {result.email}: {e}")
                    email_results[result.email] = False
        
        successful_emails = sum(1 for v in email_results.values() if v)
        logger.info(f"Email sending complete: {successful_emails}/{len(email_results)} successful")
    
    # Build response
    ready_to_send = sum(1 for r in results if r.status == "ready_to_send")
    missing = sum(1 for r in results if r.status == "missing_certificate")
    errors = sum(1 for r in results if r.status in ["invalid_id", "encoding_error", "processing_error"])
    
    return DistributionResponse(
        students=results,
        total=len(results),
        ready_to_send=ready_to_send,
        missing=missing,
        errors=errors
    )


@router.post("/distribute-certificates")
async def distribute_certificates(
    excel: UploadFile = File(...),
    zip_file: UploadFile = File(...)
):
    """
    Flow B: Distribute certificates to students via email.
    
    Purpose:
    - Receives ZIP of PDFs uploaded by frontend
    - Receives Excel with ID + Email columns
    - Parses Excel → list of { id, email }
    - Matches by ID → locates correct PDF in ZIP
    - Sends each student their own certificate via email
    
    Args:
        excel: Excel file with student data (must include ID and Email columns)
        zip_file: ZIP file containing PDF certificates
        
    Returns:
        JSON summary with distribution results
    """
    logger.info("Flow B - Certificate distribution request received")
    
    # Validate Excel file
    if not excel.filename or not excel.filename.endswith((".xlsx", ".xls")):
        logger.warning(f"Invalid Excel file type: {excel.filename}")
        raise HTTPException(
            status_code=400,
            detail="Excel file must be .xlsx or .xls"
        )
    
    # Validate ZIP file
    if not zip_file.filename or not zip_file.filename.endswith(".zip"):
        logger.warning(f"Invalid ZIP file type: {zip_file.filename}")
        raise HTTPException(
            status_code=400,
            detail="Must upload a ZIP file of certificates"
        )
    
    # Read Excel file
    try:
        excel_bytes = await excel.read()
        logger.info(f"Excel file read: {len(excel_bytes)} bytes")
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {e}")
    
    # Read ZIP file
    try:
        zip_bytes = await zip_file.read()
        logger.info(f"ZIP file read: {len(zip_bytes)} bytes")
    except Exception as e:
        logger.error(f"Failed to read ZIP file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read ZIP file: {e}")
    
    # Process distribution
    try:
        results = distributor.process(excel_bytes, zip_bytes)
        logger.info(f"Distribution processed: {len(results)} students")
    except ValueError as e:
        logger.error(f"Distribution processing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in distribution: {e}")
        raise HTTPException(status_code=500, detail=f"Distribution processing error: {e}")
    
    # Send emails to students
    logger.info("Sending emails to students...")
    successful_emails = 0
    failed_emails = 0
    
    # Create a list to track updated results with status changes
    updated_results = []
    
    for result in results:
        # Only send emails for students with ready_to_send status
        if result.status == "ready_to_send":
            if not result.email:
                logger.error(f"Student email missing for ID {result.id}")
                updated_results.append(result)  # Keep original status
                failed_emails += 1
                continue
            
            if not result.file_base64:
                logger.error(f"PDF file missing for ID {result.id}")
                updated_results.append(result)  # Keep original status
                failed_emails += 1
                continue
            
            try:
                import base64
                pdf_bytes = base64.b64decode(result.file_base64)
                filename = result.filename or f"certificate_{result.id}.pdf"
                
                logger.info(f"Sending certificate to student {result.email} (ID: {result.id})")
                success = email_service.send_certificate_to_student(
                    result.email,
                    pdf_bytes,
                    filename
                )
                
                if success:
                    successful_emails += 1
                    logger.info(f"Email sent successfully to {result.email}")
                    # Update status to "sent"
                    updated_result = result.model_copy(update={"status": "sent"})
                    updated_results.append(updated_result)
                else:
                    failed_emails += 1
                    logger.error(f"Failed to send email to {result.email}")
                    # Keep status as "ready_to_send" if email failed
                    updated_results.append(result)
            except Exception as e:
                logger.error(f"Failed to send email to {result.email}: {e}")
                failed_emails += 1
                # Keep status as "ready_to_send" if exception occurred
                updated_results.append(result)
        else:
            # Keep other statuses unchanged
            updated_results.append(result)
    
    logger.info(f"Email sending complete: {successful_emails} successful, {failed_emails} failed")
    
    # Build response summary using updated results
    ready_to_send = sum(1 for r in updated_results if r.status == "ready_to_send")
    sent = sum(1 for r in updated_results if r.status == "sent")
    missing_certificates = sum(1 for r in updated_results if r.status == "missing_certificate")
    missing_emails = sum(1 for r in updated_results if r.status == "missing_email")
    invalid_ids = sum(1 for r in updated_results if r.status == "invalid_id")
    other_errors = sum(1 for r in updated_results if r.status in ["encoding_error", "processing_error"])
    
    return {
        "status": "success",
        "total_students": len(updated_results),
        "emails_sent": successful_emails,
        "emails_failed": failed_emails,
        "missing_certificates": missing_certificates,
        "students": [
            {
                "id": r.id,
                "email": r.email,
                "status": r.status
            }
            for r in updated_results
        ]
    }

