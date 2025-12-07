# Auto-Certificate Backend Flow Guide

## 🔵 1. Project Overview

### What the Backend Does

The Auto-Certificate backend is a FastAPI-based certificate generation and distribution system that:

- **Generates PDF certificates** from student data with Hebrew/RTL text support
- **Creates ZIP archives** of multiple certificates
- **Distributes certificates** to students via email
- **Manages certificate templates** (upload/download)
- **Processes Excel files** to extract student information

### Two Major Flows

#### Flow A: Certificate Generation (ZIP → Admin)
1. Receives student data as JSON
2. Generates individual PDF certificates
3. Bundles certificates into a ZIP file
4. Emails the ZIP file to the admin email address

#### Flow B: Certificate Distribution (Email → Students)
1. Receives a ZIP file containing PDF certificates
2. Receives an Excel file with student IDs and emails
3. Matches certificates to students by ID number
4. Sends each student their certificate via email

### Technologies Used

- **FastAPI** - Web framework and API server
- **Pillow (PIL)** - Image processing and PDF generation
- **Pandas** - Excel file parsing
- **SMTP (smtplib)** - Email sending
- **Docker** - Containerization
- **Nginx** - Reverse proxy (optional)
- **Python 3.12** - Runtime environment

---

## 🔵 2. Environment Variables

The backend requires the following environment variables. Create a `.env` file in the `backend/` directory or set them in your deployment environment.

### SMTP Configuration (for sending to students)

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` | ✅ Yes |
| `SMTP_PORT` | SMTP server port (465 for SSL, 587 for TLS) | `465` | ✅ Yes |
| `SMTP_USER` | SMTP authentication username | `study@connectedbusinesses.co.il` | ✅ Yes |
| `SMTP_PASS` | SMTP authentication password | `your-app-password` | ✅ Yes |
| `SMTP_USE_SSL` | Use SSL connection (for port 465) | `true` | ✅ Yes |
| `SMTP_USE_TLS` | Use TLS connection (for port 587) | `false` | ⚠️ If SSL=false |
| `EMAIL_FROM` | From email address (display name optional) | `"COB Academy <study@connectedbusinesses.co.il>"` | ✅ Yes |

**Note**: For Gmail, use an App Password instead of your regular password. Enable 2FA and generate an app password in your Google Account settings.

### Admin Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `ADMIN_RESULTS_EMAIL` | Email address to receive ZIP files from Flow A | `aviamar@lionstars.co.il` | ✅ Yes |

### Paths & System Settings

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `TEMPLATE_PATH` | Path to certificate template image | `/app/data/template.png` | ⚠️ Default provided |
| `FIELDS_CONFIG_PATH` | Path to fields configuration JSON | `/app/fields_config.json` | ⚠️ Default provided |
| `FONTS_DIR` | Directory containing font files | `/app/fonts` | ⚠️ Default provided |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` | ⚠️ Default: INFO |

### Optional Settings

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DEBUG` | Enable debug mode | `False` | ❌ No |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `https://jabanes.github.io` | ❌ No |

### Example `.env` File

```env
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=study@connectedbusinesses.co.il
SMTP_PASS=your-app-password-here
SMTP_USE_SSL=true
SMTP_USE_TLS=false
EMAIL_FROM="COB Academy <study@connectedbusinesses.co.il>"

# Admin Configuration
ADMIN_RESULTS_EMAIL=aviamar@lionstars.co.il

# Paths & System
TEMPLATE_PATH=/app/data/template.png
FIELDS_CONFIG_PATH=/app/fields_config.json
FONTS_DIR=/app/fonts
LOG_LEVEL=INFO

# Optional
DEBUG=False
CORS_ORIGINS=https://jabanes.github.io
```

---

## 🔵 3. Endpoints Documentation

### ENDPOINT: POST /generate-certificates-batch

**Flow A: Generate certificates and email ZIP to admin**

#### Description:
Generates PDF certificates from JSON student data, creates a ZIP file, and automatically emails it to the admin email address configured in `ADMIN_RESULTS_EMAIL`.

#### Request Body (JSON):
```json
{
  "students": [
    {
      "field1": "Student Name",
      "field2": "123456789",
      "field3": "Additional Field"
    }
  ],
  "zip_name": "certificates.zip"
}
```

**Fields:**
- `students` (array, required): List of student objects
  - `field1` (string): Student name
  - `field2` (string): Student ID number (ת.ז)
  - `field3` (string, optional): Additional certificate field
- `zip_name` (string, optional): Name for the ZIP file (default: "certificates.zip")

#### Response:
**Success (200 OK):**
```json
{
  "status": "success",
  "message": "Certificates generated and ZIP sent to admin",
  "students_processed": 5,
  "certificates_generated": 5,
  "zip_size_bytes": 2456789,
  "zip_filename": "certificates.zip"
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "No valid students provided"
}
```

**Error (500 Internal Server Error):**
```json
{
  "detail": "Certificate generation failed: Template file not found"
}
```

#### Example CURL:
```bash
curl -X POST http://localhost:8000/generate-certificates-batch \
  -H "Content-Type: application/json" \
  -d '{
    "students": [
      {"field1": "ארז חבני", "field2": "123456789", "field3": "1001"},
      {"field1": "יונתן גויכמן", "field2": "987654321", "field3": "1002"}
    ],
    "zip_name": "cob_certificates_2024.zip"
  }'
```

**What Happens:**
1. System validates student data
2. Generates PDF for each student
3. Creates ZIP file with all certificates
4. Sends ZIP to `ADMIN_RESULTS_EMAIL` with subject "Cob Certificates – ZIP Batch Result"
5. Returns JSON success response

---

### ENDPOINT: POST /distribute-certificates

**Flow B: Distribute certificates to students via email**

#### Description:
Matches PDF certificates from a ZIP file with students from an Excel file, then sends each student their certificate via email.

#### Request Body (multipart/form-data):
- `excel` (file, required): Excel file (.xlsx or .xls) containing student data
- `zip_file` (file, required): ZIP file containing PDF certificates

**Excel File Requirements:**
- Must contain columns for **ID** (ת.ז) and **Email** (אימייל)
- ID column can be named: "ת.ז", "תז", "מספר זהות", "ID", "field2"
- Email column can be named: "אימייל", "דואל", "email", "Email"
- PDF filenames in ZIP must contain the student ID (7-9 digits)

#### Response:
**Success (200 OK):**
```json
{
  "status": "success",
  "message": "Certificate distribution completed",
  "total_students": 10,
  "ready_to_send": 8,
  "emails_sent": 8,
  "emails_failed": 0,
  "missing_certificates": 2,
  "errors": 0,
  "students": [
    {
      "id": "123456789",
      "email": "student@example.com",
      "filename": "תעודת סיום 123456789.pdf",
      "file_base64": "JVBERi0xLjQKJeLjz9MK...",
      "status": "ready_to_send"
    },
    {
      "id": "987654321",
      "email": "student2@example.com",
      "status": "missing_certificate"
    }
  ]
}
```

**Status Values:**
- `ready_to_send`: Certificate found and email sent successfully
- `missing_certificate`: No matching PDF found in ZIP for this ID
- `invalid_id`: Student ID is missing or invalid
- `encoding_error`: Failed to encode PDF to Base64
- `processing_error`: Error processing student record

#### Example CURL:
```bash
curl -X POST http://localhost:8000/distribute-certificates \
  -F "excel=@students.xlsx" \
  -F "zip_file=@certificates.zip"
```

**What Happens:**
1. System parses Excel file to extract student IDs and emails
2. Extracts PDF files from ZIP
3. Matches PDFs to students by extracting ID from filename (regex: `\d{7,9}`)
4. Sends email to each student with their certificate attached
5. Returns JSON summary with results

---

### ENDPOINT: POST /template

**Upload a new certificate template**

#### Description:
Uploads a new PNG or JPG image to use as the certificate template.

#### Request Body (multipart/form-data):
- `file` (file, required): Image file (PNG or JPG, max 10MB)

#### Response:
**Success (200 OK):**
```json
{
  "status": "success",
  "message": "Template updated successfully"
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "Only PNG or JPG files are allowed"
}
```

#### Example CURL:
```bash
curl -X POST http://localhost:8000/template \
  -F "file=@certificate-template.png"
```

---

### ENDPOINT: GET /template

**Download the current certificate template**

#### Description:
Returns the current certificate template image file.

#### Response:
**Success (200 OK):**
- Content-Type: `image/png`
- File download

**Error (404 Not Found):**
```json
{
  "detail": "Template file not found"
}
```

#### Example CURL:
```bash
curl -X GET http://localhost:8000/template \
  --output template.png
```

---

### ENDPOINT: GET /health

**Health check endpoint**

#### Description:
Simple readiness check to verify the backend is running.

#### Response:
**Success (200 OK):**
```json
{
  "status": "ok",
  "message": "Certificate Generation Backend is running",
  "version": "2.0.0"
}
```

#### Example CURL:
```bash
curl -X GET http://localhost:8000/health
```

---

## 🔵 4. Complete Flow Simulation Guide

This guide walks you through testing the entire system end-to-end using `curl` commands.

### Prerequisites

1. **Backend running**: `docker compose up` or `python -m app.main`
2. **Environment configured**: `.env` file with SMTP credentials
3. **Test files ready**:
   - `certificate-template.png` - Template image
   - `students.xlsx` - Excel file with student data
   - `certificates.zip` - ZIP file with PDF certificates (for Flow B)

### Step 1: Upload a New Template

Upload the certificate template image that will be used for all certificate generation.

```bash
curl -X POST http://localhost:8000/template \
  -F "file=@certificate-template.png"
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Template updated successfully"
}
```

**Verification:**
- Check logs: `tail -f backend/logs/backend.log`
- Should see: `"Template saved successfully to /app/data/template.png"`

---

### Step 2: Generate Certificates ZIP (Flow A)

Generate certificates from JSON student data and automatically email ZIP to admin.

```bash
curl -X POST http://localhost:8000/generate-certificates-batch \
  -H "Content-Type: application/json" \
  -d '{
    "students": [
      {
        "field1": "ארז חבני",
        "field2": "123456789",
        "field3": "1001"
      },
      {
        "field1": "יונתן גויכמן",
        "field2": "987654321",
        "field3": "1002"
      }
    ],
    "zip_name": "cob_certificates_test.zip"
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Certificates generated and ZIP sent to admin",
  "students_processed": 2,
  "certificates_generated": 2,
  "zip_size_bytes": 1234567,
  "zip_filename": "cob_certificates_test.zip"
}
```

**What Happens:**
1. ✅ System parses JSON student data
2. ✅ Generates PDF certificate for each student
3. ✅ Creates ZIP file with all certificates
4. ✅ Sends ZIP to `ADMIN_RESULTS_EMAIL` via email
5. ✅ Returns success JSON

**Check Admin Email:**
- Subject: "Cob Certificates – ZIP Batch Result"
- Attachment: `cob_certificates_test.zip`
- Body: "The certificate generation batch has been completed. Please find the ZIP file attached."

**Logs to Check:**
```
INFO - Parsed 2 students from JSON
INFO - Generated 2 certificates
INFO - ZIP file created: 1234567 bytes
INFO - Sending ZIP file to admin: aviamar@lionstars.co.il
INFO - ZIP file sent successfully to aviamar@lionstars.co.il
```

---

### Step 3: Test Distribution (Flow B)

Distribute certificates from a ZIP file to students via email.

**Prepare Excel File (`students.xlsx`):**
| שם | ת.ז | אימייל |
|----|-----|--------|
| ארז חבני | 123456789 | erez@example.com |
| יונתן גויכמן | 987654321 | yonatan@example.com |

**Prepare ZIP File (`certificates.zip`):**
- Contains PDF files with IDs in filenames:
  - `certificate-123456789.pdf`
  - `certificate-987654321.pdf`

**Send Request:**
```bash
curl -X POST http://localhost:8000/distribute-certificates \
  -F "excel=@students.xlsx" \
  -F "zip_file=@certificates.zip"
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Certificate distribution completed",
  "total_students": 2,
  "ready_to_send": 2,
  "emails_sent": 2,
  "emails_failed": 0,
  "missing_certificates": 0,
  "errors": 0,
  "students": [
    {
      "id": "123456789",
      "email": "erez@example.com",
      "filename": "תעודת סיום 123456789.pdf",
      "file_base64": "JVBERi0xLjQKJeLjz9MK...",
      "status": "ready_to_send"
    },
    {
      "id": "987654321",
      "email": "yonatan@example.com",
      "filename": "תעודת סיום 987654321.pdf",
      "file_base64": "JVBERi0xLjQKJeLjz9MK...",
      "status": "ready_to_send"
    }
  ]
}
```

**What Happens:**
1. ✅ System parses Excel file
2. ✅ Extracts student IDs and emails
3. ✅ Extracts PDF files from ZIP
4. ✅ Matches PDFs to students by ID (extracted from filename)
5. ✅ Sends email to each student with their certificate
6. ✅ Returns summary JSON

**Check Student Emails:**
- Subject: "תעודת סיום - COB Academy"
- Attachment: PDF certificate file
- Body: HTML email with Hebrew text

**Logs to Check:**
```
INFO - Excel file read: 12345 bytes
INFO - ZIP file read: 2345678 bytes
INFO - Parsed 2 students from Excel
INFO - Found 2 certificates in ZIP
INFO - Distribution processed: 2 students
INFO - Sending certificate to student erez@example.com (ID: 123456789)
INFO - Certificate sent successfully to erez@example.com
INFO - Email sending complete: 2 successful, 0 failed
```

---

### Excel File Processing Details

**What is Extracted from Excel:**
- **ID Column**: Recognizes Hebrew names: "ת.ז", "תז", "מספר זהות", "תעודת זהות"
- **Email Column**: Recognizes Hebrew names: "אימייל", "דואל"
- **Name Column**: Optional, recognized as "שם" or "field1"
- **Additional Fields**: Any other columns are preserved

**ID Matching Process:**
1. System extracts ID from Excel (cleans non-digits)
2. Extracts ID from PDF filename using regex: `\d{7,9}`
3. Matches IDs exactly (must be 7-9 digits)
4. If match found, associates PDF with student

**Example Filename Matching:**
- `certificate-123456789.pdf` → ID: `123456789`
- `תעודה_987654321.pdf` → ID: `987654321`
- `student_1234567_cert.pdf` → ID: `1234567`

---

### Errors & Edge Cases

#### Missing Email
**Scenario**: Student has ID but no email address

**Response:**
```json
{
  "id": "123456789",
  "email": "",
  "status": "ready_to_send"
}
```

**Log:**
```
ERROR - Student email missing for ID 123456789
```

**Result**: Certificate matched but email not sent

---

#### Missing PDF
**Scenario**: Student in Excel but no matching PDF in ZIP

**Response:**
```json
{
  "id": "123456789",
  "email": "student@example.com",
  "status": "missing_certificate"
}
```

**Log:**
```
WARNING - No matching PDF found for student ID 123456789
```

**Result**: Email not sent, status marked as "missing_certificate"

---

#### Invalid ID
**Scenario**: Student ID is empty or contains non-digits

**Response:**
```json
{
  "id": "",
  "email": "student@example.com",
  "status": "invalid_id"
}
```

**Log:**
```
WARNING - Invalid student ID for student student@example.com
```

**Result**: Cannot match, email not sent

---

#### Encoding Error
**Scenario**: PDF file exists but Base64 encoding fails

**Response:**
```json
{
  "id": "123456789",
  "email": "student@example.com",
  "status": "encoding_error"
}
```

**Log:**
```
ERROR - Base64 encoding failed for student 123456789: ...
```

**Result**: Email not sent

---

## 🔵 5. Email Template Details

### Template Location
**Path**: `backend/app/templates/certificate_email.html`

### Placeholder System

The email template uses a placeholder system:

**Placeholder**: `{{EMAIL_BODY}}`

**How It Works:**
1. Template file is loaded from disk
2. `{{EMAIL_BODY}}` is replaced with actual email content
3. Final HTML is sent as email body

**Example Replacement:**
```html
<!-- Template file -->
<div class="content">
    {{EMAIL_BODY}}
</div>

<!-- After replacement -->
<div class="content">
    <p>שלום,</p>
    <p>מצורף למייל תעודת הסיום שלך.</p>
    <p>אנא שמור את הקובץ במקום בטוח.</p>
    <p>בברכה,<br>צוות COB Academy</p>
</div>
```

### Encoding Notes

- **File Encoding**: UTF-8 (required for Hebrew text)
- **Email Encoding**: UTF-8 charset specified in MIME headers
- **RTL Support**: Template includes `dir="rtl"` and `lang="he"` attributes

### Attachment Handling

PDF attachments are included using MIME multipart:

1. **HTML Body**: Email content with template
2. **PDF Attachment**: Certificate file attached as `application/pdf`
3. **MIME Boundaries**: Automatically handled by `email.mime.multipart`

**Attachment Headers:**
```
Content-Disposition: attachment; filename="תעודת סיום 123456789.pdf"
Content-Type: application/pdf
```

### Customizing the Template

To customize the email template:

1. Edit `backend/app/templates/certificate_email.html`
2. Keep the `{{EMAIL_BODY}}` placeholder where content should go
3. Modify styling, layout, or add additional content
4. Restart the backend to load changes

**Note**: The template is loaded from disk each time an email is sent, so changes take effect immediately after restart.

---

## 🔵 6. Logs Guide

### Log File Location

**Path**: `/app/logs/backend.log` (inside container)
**Local Path**: `backend/logs/backend.log` (when running locally)

### Log Format

```
2025-12-07 14:30:09 - backend - INFO - function_name:40 - Log message here
```

**Format Breakdown:**
- Timestamp: `2025-12-07 14:30:09`
- Logger Name: `backend`
- Level: `INFO`, `WARNING`, `ERROR`, `DEBUG`
- Function: `function_name:line_number`
- Message: `Log message here`

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages (non-critical issues)
- **ERROR**: Error messages (failures)
- **CRITICAL**: Critical errors (system failures)

**Configure via**: `LOG_LEVEL` environment variable

### Viewing Logs

#### Local Development
```bash
# Tail logs in real-time
tail -f backend/logs/backend.log

# View last 100 lines
tail -n 100 backend/logs/backend.log

# Search for errors
grep ERROR backend/logs/backend.log
```

#### Docker Container
```bash
# Tail logs in real-time
docker logs certificate-backend -f

# View last 100 lines
docker logs certificate-backend --tail 100

# Follow logs with timestamps
docker logs certificate-backend -f --timestamps

# Search for errors
docker logs certificate-backend 2>&1 | grep ERROR
```

### Common Log Messages

**Flow A (Generation):**
```
INFO - Batch generation request received: 5 students
INFO - Parsed 5 students from JSON
INFO - Generated PDF for student: ארז חבני (ID: 123456789)
INFO - Generated 5 certificates
INFO - ZIP file created: 2345678 bytes
INFO - Sending ZIP file to admin: aviamar@lionstars.co.il
INFO - ZIP file sent successfully to aviamar@lionstars.co.il
```

**Flow B (Distribution):**
```
INFO - Certificate distribution request received
INFO - Excel file read: 12345 bytes
INFO - ZIP file read: 2345678 bytes
INFO - Parsed 10 students from Excel
INFO - Found 8 certificates in ZIP
INFO - Distribution processed: 10 students
INFO - Sending certificate to student student@example.com (ID: 123456789)
INFO - Certificate sent successfully to student@example.com
ERROR - Student email missing for ID 987654321
WARNING - No matching PDF found for student ID 111111111
INFO - Email sending complete: 8 successful, 2 failed
```

**Errors:**
```
ERROR - Failed to read Excel file: ...
ERROR - Certificate generation failed: Template file not found
ERROR - Failed to send ZIP to admin: ...
ERROR - Failed to send certificate to student@example.com: ...
```

---

## 🔵 7. Docker & Deployment Guide

### Local Development

#### Start Services
```bash
# Build and start all services
docker compose up --build

# Start in detached mode (background)
docker compose up -d --build

# Start only backend
docker compose up backend
```

#### Stop Services
```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

#### Restart Backend
```bash
# Restart backend container
docker compose restart backend

# Rebuild and restart
docker compose up -d --build backend
```

#### View Logs
```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail 100 backend
```

### Container Management

#### Execute Commands Inside Container
```bash
# Open bash shell
docker exec -it certificate-backend bash

# Run Python command
docker exec -it certificate-backend python -m app.main

# Check environment variables
docker exec -it certificate-backend env | grep SMTP
```

#### Copy Files to/from Container
```bash
# Copy file from container
docker cp certificate-backend:/app/logs/backend.log ./backend.log

# Copy file to container
docker cp ./template.png certificate-backend:/app/data/template.png
```

### Environment Variables in Docker

**Option 1: `.env` File**
```bash
# Create .env file in project root
cp backend/.env.example backend/.env
# Edit backend/.env with your values

# Docker Compose automatically loads .env
docker compose up
```

**Option 2: Environment Variables**
```bash
# Set in docker-compose.yml
environment:
  - SMTP_HOST=smtp.gmail.com
  - SMTP_PASS=your-password

# Or pass via command line
docker compose run -e SMTP_PASS=your-password backend
```

### Production Deployment

#### Build Image
```bash
cd backend
docker build -t certificate-backend:latest .
```

#### Run Container
```bash
docker run -d \
  --name certificate-backend \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  certificate-backend:latest
```

#### Health Check
```bash
# Check health endpoint
curl http://localhost:8000/health

# Check container status
docker ps | grep certificate-backend

# Check container logs
docker logs certificate-backend
```

### Troubleshooting

#### Container Won't Start
```bash
# Check logs
docker compose logs backend

# Check environment variables
docker compose config

# Verify .env file exists
ls -la backend/.env
```

#### SMTP Connection Issues
```bash
# Test SMTP from container
docker exec -it certificate-backend python -c "
import smtplib
server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login('your-email', 'your-password')
print('SMTP connection successful')
"
```

#### Permission Issues
```bash
# Fix log directory permissions
docker exec -it certificate-backend chmod -R 777 /app/logs

# Fix data directory permissions
docker exec -it certificate-backend chmod -R 777 /app/data
```

---

## 🔵 8. Validation Examples

### Edge Case Testing

#### 1. Upload Invalid Excel File

**Test**: Upload a non-Excel file as Excel

```bash
curl -X POST http://localhost:8000/distribute-certificates \
  -F "excel=@test.txt" \
  -F "zip_file=@certificates.zip"
```

**Expected Response:**
```json
{
  "detail": "Excel file must be .xlsx or .xls"
}
```

**Status Code**: `400 Bad Request`

---

#### 2. Upload Bad ZIP File

**Test**: Upload corrupted or invalid ZIP file

```bash
curl -X POST http://localhost:8000/distribute-certificates \
  -F "excel=@students.xlsx" \
  -F "zip_file=@corrupted.zip"
```

**Expected Response:**
```json
{
  "detail": "Invalid or corrupted ZIP file"
}
```

**Status Code**: `400 Bad Request`

**Log:**
```
ERROR - Invalid or corrupted ZIP file
```

---

#### 3. Missing Required Fields

**Test**: Send JSON without required `students` field

```bash
curl -X POST http://localhost:8000/generate-certificates-batch \
  -H "Content-Type: application/json" \
  -d '{"zip_name": "test.zip"}'
```

**Expected Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "students"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Status Code**: `422 Unprocessable Entity`

---

#### 4. Student with No Email

**Test**: Excel contains student with ID but no email

**Excel Content:**
| שם | ת.ז | אימייל |
|----|-----|--------|
| ארז חבני | 123456789 | |

**Request:**
```bash
curl -X POST http://localhost:8000/distribute-certificates \
  -F "excel=@students_no_email.xlsx" \
  -F "zip_file=@certificates.zip"
```

**Expected Response:**
```json
{
  "students": [
    {
      "id": "123456789",
      "email": "",
      "status": "ready_to_send"
    }
  ],
  "emails_sent": 0,
  "emails_failed": 1
}
```

**Log:**
```
ERROR - Student email missing for ID 123456789
WARNING - Failed to send email to : Email address is empty
```

---

#### 5. Non-Numeric ID Fields

**Test**: Student ID contains letters or special characters

**Excel Content:**
| שם | ת.ז | אימייל |
|----|-----|--------|
| ארז חבני | ABC123 | student@example.com |

**Request:**
```bash
curl -X POST http://localhost:8000/distribute-certificates \
  -F "excel=@students_invalid_id.xlsx" \
  -F "zip_file=@certificates.zip"
```

**Expected Response:**
```json
{
  "students": [
    {
      "id": "123",
      "email": "student@example.com",
      "status": "invalid_id"
    }
  ]
}
```

**What Happens:**
- System extracts only digits: `ABC123` → `123`
- If cleaned ID is less than 7 digits, marked as `invalid_id`
- Email not sent

**Log:**
```
WARNING - Invalid student ID for student student@example.com: ABC123
```

---

#### 6. Empty Students Array

**Test**: Send empty students array

```bash
curl -X POST http://localhost:8000/generate-certificates-batch \
  -H "Content-Type: application/json" \
  -d '{"students": [], "zip_name": "test.zip"}'
```

**Expected Response:**
```json
{
  "detail": "No valid students provided"
}
```

**Status Code**: `400 Bad Request`

---

#### 7. Template Not Found

**Test**: Generate certificates without uploading template first

```bash
curl -X POST http://localhost:8000/generate-certificates-batch \
  -H "Content-Type: application/json" \
  -d '{
    "students": [{"field1": "Test", "field2": "123456789"}],
    "zip_name": "test.zip"
  }'
```

**Expected Response:**
```json
{
  "detail": "Template file not found: /app/data/template.png"
}
```

**Status Code**: `500 Internal Server Error`

**Solution**: Upload template first using `POST /template`

---

#### 8. Invalid Template File Type

**Test**: Upload non-image file as template

```bash
curl -X POST http://localhost:8000/template \
  -F "file=@test.txt"
```

**Expected Response:**
```json
{
  "detail": "Only PNG or JPG files are allowed"
}
```

**Status Code**: `400 Bad Request`

---

#### 9. Template File Too Large

**Test**: Upload template larger than 10MB

```bash
curl -X POST http://localhost:8000/template \
  -F "file=@huge_template.png"
```

**Expected Response:**
```json
{
  "detail": "File too large (max 10485760 bytes)"
}
```

**Status Code**: `400 Bad Request`

---

#### 10. SMTP Not Configured

**Test**: Try to send email without SMTP credentials

**Expected Behavior:**
- Request completes successfully
- Email not sent
- Log shows warning

**Log:**
```
WARNING - SMTP configuration incomplete. Email sending will be disabled.
ERROR - Cannot send email: SMTP not configured
```

**Response (Flow A):**
```json
{
  "status": "success",
  "message": "Certificates generated and ZIP sent to admin",
  ...
}
```

**Note**: Email failure doesn't fail the request, but is logged as an error.

---

## Quick Reference

### Common Commands

```bash
# Health check
curl http://localhost:8000/health

# Upload template
curl -X POST http://localhost:8000/template -F "file=@template.png"

# Generate certificates (Flow A)
curl -X POST http://localhost:8000/generate-certificates-batch \
  -H "Content-Type: application/json" \
  -d '{"students": [...], "zip_name": "certificates.zip"}'

# Distribute certificates (Flow B)
curl -X POST http://localhost:8000/distribute-certificates \
  -F "excel=@students.xlsx" \
  -F "zip_file=@certificates.zip"

# View logs (Docker)
docker logs certificate-backend -f

# Restart backend
docker compose restart backend
```

### File Structure

```
Auto-Certificate/
├── backend/
│   ├── app/
│   │   ├── templates/
│   │   │   └── certificate_email.html
│   │   └── ...
│   ├── data/
│   │   └── template.png
│   ├── logs/
│   │   └── backend.log
│   └── .env
├── docker-compose.yml
└── FLOW_GUIDE.md
```

---

## Support & Troubleshooting

### Common Issues

1. **SMTP Connection Failed**
   - Verify SMTP credentials in `.env`
   - Check firewall/network settings
   - For Gmail, use App Password

2. **Template Not Found**
   - Upload template using `POST /template`
   - Verify `TEMPLATE_PATH` in `.env`

3. **Fonts Not Loading**
   - Ensure fonts are in `backend/fonts/` directory
   - Check `FONTS_DIR` environment variable

4. **Logs Not Writing**
   - Check directory permissions: `chmod 777 backend/logs`
   - Verify `LOGS_DIR` path in config

5. **Docker Container Exits**
   - Check logs: `docker logs certificate-backend`
   - Verify environment variables are set
   - Check port conflicts: `netstat -an | grep 8000`

### Getting Help

- Check logs: `backend/logs/backend.log`
- Review error messages in API responses
- Verify environment variables are set correctly
- Test SMTP connection independently

---

**Last Updated**: 2025-12-07  
**Version**: 2.0.0

