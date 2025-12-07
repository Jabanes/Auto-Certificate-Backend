# Migration Guide: From N8N to FastAPI Backend

This guide explains how to migrate from the N8N workflows to the new FastAPI backend.

## Replaced N8N Workflows

### 1. Excel → Student Mapping → ZIP Generation → Email Admin

**Old N8N Workflow:**
- Extract Excel data
- Code/transform student data
- Generate certificates via HTTP request
- Create ZIP file
- Send ZIP to admin via SMTP

**New Backend Endpoint:**
```
POST /upload-excel-and-generate
```

**Request:**
- Form data with:
  - `excel`: Excel file (.xlsx or .xls)
  - `admin_email`: (optional) Admin email to receive ZIP
  - `zip_name`: (optional) Name for ZIP file

**Response:**
- ZIP file with generated certificates
- Email sent to admin if `admin_email` provided

**Example:**
```python
import requests

files = {'excel': open('students.xlsx', 'rb')}
data = {
    'admin_email': 'admin@example.com',
    'zip_name': 'certificates.zip'
}

response = requests.post(
    'http://localhost:8000/upload-excel-and-generate',
    files=files,
    data=data
)

with open('certificates.zip', 'wb') as f:
    f.write(response.content)
```

### 2. ZIP + Excel → Match PDFs → Email Students

**Old N8N Workflow:**
- Upload ZIP file with certificates
- Upload Excel with student data
- Match certificates by ID
- Send emails to students

**New Backend Endpoint:**
```
POST /send-certificates
```

**Request:**
- Form data with:
  - `excel`: Excel file with student data
  - `zip_file`: ZIP file containing PDF certificates
  - `send_emails`: Boolean (default: false)

**Response:**
```json
{
  "students": [
    {
      "id": "123456789",
      "email": "student@example.com",
      "filename": "תעודת סיום 123456789.pdf",
      "file_base64": "JVBERi0xLjQKJeLjz9MK...",
      "status": "ready_to_send"
    }
  ],
  "total": 10,
  "ready_to_send": 8,
  "missing": 2,
  "errors": 0
}
```

**Example:**
```python
import requests

files = {
    'excel': open('students.xlsx', 'rb'),
    'zip_file': open('certificates.zip', 'rb')
}
data = {
    'send_emails': 'true'  # Send emails directly
}

response = requests.post(
    'http://localhost:8000/send-certificates',
    files=files,
    data=data
)

result = response.json()
print(f"Ready to send: {result['ready_to_send']}")
print(f"Missing: {result['missing']}")
```

## Key Differences

1. **Single Backend**: All logic is now in one FastAPI backend instead of distributed across N8N nodes
2. **Better Error Handling**: Comprehensive error handling with detailed logging
3. **Pydantic Validation**: All data is validated using Pydantic models
4. **Modular Architecture**: Clean separation of concerns with services, utils, and models
5. **Hebrew Support**: Built-in support for Hebrew column names and RTL text
6. **Logging**: All operations logged to `/logs/backend.log`

## Configuration Changes

### Environment Variables

Set these in `.env` file or environment:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_USE_TLS=True
EMAIL_FROM=your-email@gmail.com
ADMIN_EMAIL=admin@example.com
```

### File Structure

- Templates stored in `/data/template.png`
- Logs in `/logs/backend.log`
- Configuration in `fields_config.json`

## Testing the Migration

1. **Test Excel Parsing:**
   ```bash
   curl -X POST "http://localhost:8000/upload-excel-and-generate" \
     -F "excel=@students.xlsx" \
     -F "admin_email=admin@example.com"
   ```

2. **Test Distribution:**
   ```bash
   curl -X POST "http://localhost:8000/send-certificates" \
     -F "excel=@students.xlsx" \
     -F "zip_file=@certificates.zip" \
     -F "send_emails=false"
   ```

3. **Check Logs:**
   ```bash
   tail -f backend/logs/backend.log
   ```

## Rollback Plan

If you need to rollback:
1. Keep N8N workflows running in parallel initially
2. Test new backend thoroughly before switching
3. Monitor logs for any issues
4. Keep old `main.py` as backup

## Support

All operations are logged. Check `/logs/backend.log` for detailed information about any issues.

