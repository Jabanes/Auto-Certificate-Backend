# Certificate Generation Backend

A modular FastAPI backend for generating and distributing certificates, replacing N8N workflows.

## Features

- **Template Management**: Upload and manage certificate templates
- **Excel Parsing**: Parse student data from Excel files with Hebrew support
- **Certificate Generation**: Generate PDF certificates with RTL text support
- **ZIP Creation**: Bundle certificates into ZIP files
- **Email Distribution**: Send certificates via SMTP
- **Comprehensive Logging**: All operations logged to `/logs/backend.log`

## Architecture

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/                    # API route handlers
│   │   ├── template_routes.py
│   │   ├── certificate_routes.py
│   │   └── distribution_routes.py
│   ├── core/                   # Core configuration
│   │   ├── config.py
│   │   └── logging_config.py
│   ├── services/               # Business logic services
│   │   ├── excel_parser.py
│   │   ├── certificate_generator.py
│   │   ├── email_service.py
│   │   └── distributor.py
│   ├── utils/                  # Utility functions
│   │   ├── zip_utils.py
│   │   ├── file_utils.py
│   │   └── text_utils.py
│   └── models/                 # Pydantic models
│       ├── student_model.py
│       ├── batch_request.py
│       └── distribution_result.py
├── data/                       # Data directory (templates stored here)
├── logs/                       # Log files
└── requirements.txt
```

## API Endpoints

### Template Management

- `GET /template` - Get current template image
- `POST /template` - Upload new template image

### Certificate Generation

- `POST /upload-excel-and-generate` - Upload Excel, generate certificates, optionally email ZIP to admin
- `POST /generate-certificates-batch` - Generate certificates from JSON payload
- `POST /generate-certificate` - Generate single certificate

### Certificate Distribution

- `POST /send-certificates` - Match certificates with students and optionally send emails
- `POST /distribute-certificates` - Legacy endpoint for distribution (no email sending)

### Health Check

- `GET /health` - Health check endpoint

## Environment Variables

Create a `.env` file in the backend directory:

```env
# Application
DEBUG=False

# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_USE_TLS=True
EMAIL_FROM=your-email@gmail.com
ADMIN_EMAIL=admin@example.com

# CORS
CORS_ORIGINS=https://jabanes.github.io,http://localhost:3000
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (see above)

3. Ensure `fields_config.json` is in the backend root directory

4. Ensure `fonts/` directory contains required fonts

5. Run the application:
```bash
python -m app.main
```

Or with uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Docker

Build and run with Docker:

```bash
cd backend
docker build -t certificate-backend .
docker run -p 8000:8000 --env-file .env certificate-backend
```

## Excel File Format

The Excel file should contain columns for:
- **Name** (field1): Student name (Hebrew: "שם")
- **ID** (field2): Student ID number (Hebrew: "ת.ז", "מספר זהות")
- **Email**: Student email address (Hebrew: "אימייל", "דואל")
- **Additional fields**: Optional field3

The parser automatically normalizes column names and recognizes Hebrew column headers.

## Certificate Matching

When distributing certificates:
1. PDF filenames should contain student ID (7-9 digits)
2. Excel file must have ID and Email columns
3. Matching is done by extracting ID from PDF filename

## Logging

All operations are logged to `/logs/backend.log` with:
- Upload operations
- Excel parsing
- Student mapping
- PDF generation
- ZIP creation
- Email sending
- Errors and warnings

## Error Handling

The system includes comprehensive error handling:
- Invalid file formats
- Missing required columns
- SMTP configuration errors
- Template loading failures
- Certificate generation errors

All errors are logged and return appropriate HTTP status codes.

