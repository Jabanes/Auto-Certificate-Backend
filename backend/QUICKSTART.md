# Quick Start Guide

## Prerequisites

- Python 3.12+
- pip

## Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   
   Create a `.env` file in the `backend` directory:
   ```env
   DEBUG=False
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASS=your-app-password
   SMTP_USE_TLS=True
   EMAIL_FROM=your-email@gmail.com
   ADMIN_EMAIL=admin@example.com
   CORS_ORIGINS=https://jabanes.github.io
   ```

5. **Verify file structure:**
   - `fields_config.json` should be in `backend/` directory
   - `fonts/` directory should contain font files
   - `data/template.png` should exist (or will be created on first template upload)

## Running the Application

### Development Mode

```bash
python -m app.main
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Testing Endpoints

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. Upload Template

```bash
curl -X POST "http://localhost:8000/template" \
  -F "file=@certificate-template.png"
```

### 3. Generate Certificates from Excel

```bash
curl -X POST "http://localhost:8000/upload-excel-and-generate" \
  -F "excel=@students.xlsx" \
  -F "admin_email=admin@example.com" \
  -F "zip_name=certificates.zip" \
  --output certificates.zip
```

### 4. Distribute Certificates

```bash
curl -X POST "http://localhost:8000/send-certificates" \
  -F "excel=@students.xlsx" \
  -F "zip_file=@certificates.zip" \
  -F "send_emails=false"
```

## Docker

### Build Image

```bash
docker build -t certificate-backend .
```

### Run Container

```bash
docker run -p 8000:8000 \
  -e SMTP_HOST=smtp.gmail.com \
  -e SMTP_PORT=587 \
  -e SMTP_USER=your-email@gmail.com \
  -e SMTP_PASS=your-password \
  certificate-backend
```

Or with `.env` file:

```bash
docker run -p 8000:8000 --env-file .env certificate-backend
```

## Troubleshooting

### Import Errors

If you get import errors, make sure you're running from the `backend` directory or have set `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/backend:$PYTHONPATH
```

### Template Not Found

If you get "Template file not found", upload a template first using the `/template` POST endpoint.

### SMTP Errors

If email sending fails:
1. Check SMTP credentials in `.env`
2. For Gmail, use an App Password instead of regular password
3. Check firewall/network settings
4. Verify SMTP settings are correct

### Logs

Check logs in `backend/logs/backend.log` for detailed error information.

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Read [MIGRATION.md](MIGRATION.md) for migration from N8N
- Check API documentation at `http://localhost:8000/docs` (Swagger UI)

