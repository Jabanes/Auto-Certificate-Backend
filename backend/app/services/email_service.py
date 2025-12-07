"""Email sending service."""
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText, MIMEBase
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging_config import logger


def load_email_template() -> str:
    """
    Load email template from disk.
    
    Returns:
        Email template HTML as string
    """
    template_path = Path(__file__).parent.parent / "templates" / "certificate_email.html"
    try:
        return template_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to load email template: {e}. Using default template.")
        return """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head><meta charset="UTF-8"></head>
<body>
    <div style="font-family: Arial, sans-serif; direction: rtl; text-align: right;">
        {{EMAIL_BODY}}
    </div>
</body>
</html>"""


class EmailService:
    """Service for sending emails via SMTP."""
    
    def __init__(self):
        """Initialize email service with SMTP settings."""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_pass = settings.SMTP_PASS
        self.use_ssl = settings.SMTP_USE_SSL
        self.use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.EMAIL_FROM or settings.SMTP_USER or "noreply@certificate.local"
        
        if not all([self.smtp_host, self.smtp_user, self.smtp_pass]):
            logger.warning("SMTP configuration incomplete. Email sending will be disabled.")
    
    def _is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return all([self.smtp_host, self.smtp_user, self.smtp_pass])
    
    def _connect_smtp(self) -> smtplib.SMTP:
        """
        Create and configure SMTP connection.
        
        Returns:
            Configured SMTP server object
        """
        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            if self.use_tls:
                server.starttls()
        
        server.login(self.smtp_user, self.smtp_pass)
        return server
    
    def send_admin_zip(self, zip_bytes: bytes, filename: str = "certificates.zip") -> bool:
        """
        Send ZIP file to admin results email.
        
        Args:
            zip_bytes: ZIP file content as bytes
            filename: Name for the ZIP file attachment
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self._is_configured():
            logger.error("Cannot send email: SMTP not configured")
            return False
        
        admin_email = settings.ADMIN_RESULTS_EMAIL
        if not admin_email:
            logger.error("ADMIN_RESULTS_EMAIL not configured")
            return False
        
        logger.info(f"Sending ZIP file to admin: {admin_email}")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = admin_email
            msg['Subject'] = "Cob Certificates – ZIP Batch Result"
            
            body = "The certificate generation batch has been completed. Please find the ZIP file attached."
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Attach ZIP file
            attachment = MIMEApplication(zip_bytes, _subtype='zip')
            attachment.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(attachment)
            
            # Send email
            with self._connect_smtp() as server:
                server.send_message(msg)
            
            logger.info(f"ZIP file sent successfully to {admin_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send ZIP to admin {admin_email}: {e}")
            return False
    
    def send_certificate_to_student(
        self,
        student_email: str,
        pdf_bytes: bytes,
        pdf_filename: str = "certificate.pdf"
    ) -> bool:
        """
        Send certificate PDF to student email using HTML template.
        
        Args:
            student_email: Student email address
            pdf_bytes: PDF file content as bytes
            pdf_filename: Name for the PDF file attachment
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self._is_configured():
            logger.error("Cannot send email: SMTP not configured")
            return False
        
        if not student_email:
            logger.error("Student email is missing")
            return False
        
        logger.info(f"Sending certificate to student: {student_email}")
        
        try:
            # Load email template
            template_html = load_email_template()
            
            # Replace placeholder with email body
            email_body = """
            <p>שלום,</p>
            <p>מצורף למייל תעודת הסיום שלך.</p>
            <p>אנא שמור את הקובץ במקום בטוח.</p>
            <p>בברכה,<br>צוות COB Academy</p>
            """
            html_content = template_html.replace("{{EMAIL_BODY}}", email_body)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = student_email
            msg['Subject'] = "תעודת סיום - COB Academy"
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Attach PDF file
            attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
            attachment.add_header('Content-Disposition', f'attachment; filename="{pdf_filename}"')
            msg.attach(attachment)
            
            # Send email
            with self._connect_smtp() as server:
                server.send_message(msg)
            
            logger.info(f"Certificate sent successfully to {student_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send certificate to {student_email}: {e}")
            return False
    
    def send_zip_to_admin(self, email: str, zip_bytes: bytes, zip_filename: str = "certificates.zip") -> bool:
        """
        Legacy method: Send ZIP file to specified admin email.
        
        Args:
            email: Admin email address
            zip_bytes: ZIP file content as bytes
            zip_filename: Name for the ZIP file attachment
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self._is_configured():
            logger.error("Cannot send email: SMTP not configured")
            return False
        
        logger.info(f"Sending ZIP file to admin: {email}")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = "Certificate Generation Complete"
            
            body = "The certificate generation batch has been completed. Please find the ZIP file attached."
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Attach ZIP file
            attachment = MIMEApplication(zip_bytes, _subtype='zip')
            attachment.add_header('Content-Disposition', f'attachment; filename="{zip_filename}"')
            msg.attach(attachment)
            
            # Send email
            with self._connect_smtp() as server:
                server.send_message(msg)
            
            logger.info(f"ZIP file sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send ZIP to admin {email}: {e}")
            return False
    
    def send_certificate(
        self,
        email: str,
        pdf_bytes: bytes,
        filename: str = "certificate.pdf",
        subject: Optional[str] = None
    ) -> bool:
        """
        Legacy method: Send certificate PDF to email.
        
        Args:
            email: Email address
            pdf_bytes: PDF file content as bytes
            filename: Name for the PDF file attachment
            subject: Email subject (default: "Your Certificate")
            
        Returns:
            True if sent successfully, False otherwise
        """
        return self.send_certificate_to_student(email, pdf_bytes, filename)
    
    def send_batch_certificates(
        self,
        recipients: list[tuple[str, bytes, str]]
    ) -> dict[str, bool]:
        """
        Send certificates to multiple recipients.
        
        Args:
            recipients: List of tuples (email, pdf_bytes, filename)
            
        Returns:
            Dictionary mapping email to success status
        """
        results = {}
        
        for email, pdf_bytes, filename in recipients:
            success = self.send_certificate_to_student(email, pdf_bytes, filename)
            results[email] = success
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Batch email sending complete: {successful}/{len(recipients)} successful")
        
        return results
