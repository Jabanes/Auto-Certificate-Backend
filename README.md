# Auto-Certificate

A complete certificate generation and distribution system with FastAPI backend and web frontend.

## Project Structure

```
Auto-Certificate/
├── backend/          # FastAPI backend server
│   ├── app/          # Application code
│   ├── data/         # Template storage
│   ├── fonts/        # Font files
│   ├── logs/         # Log files
│   └── ...
├── frontend/          # Static web frontend
│   └── index.html
├── docker-compose.yml # Docker orchestration
├── .env              # Environment variables (create from .env.example)
└── README.md         # This file
```

## Quick Start

### Using Docker Compose (Recommended)

1. **Copy environment variables:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** with your SMTP settings

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **Access:**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Manual Setup

#### Backend

1. **Navigate to backend:**
   ```bash
   cd backend
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables** (see `.env.example`)

4. **Run server:**
   ```bash
   python -m app.main
   ```

See [backend/README.md](backend/README.md) for detailed backend documentation.

#### Frontend

Place your HTML/JS files in the `frontend/` directory. They will be served by nginx when using docker-compose, or use any static file server.

## Features

- ✅ **Template Management**: Upload and manage certificate templates
- ✅ **Excel Parsing**: Parse student data from Excel files with Hebrew support
- ✅ **Certificate Generation**: Generate PDF certificates with RTL text support
- ✅ **ZIP Creation**: Bundle certificates into ZIP files
- ✅ **Email Distribution**: Send certificates via SMTP
- ✅ **Comprehensive Logging**: All operations logged

## API Endpoints

- `GET /health` - Health check
- `GET /template` - Get current template
- `POST /template` - Upload new template
- `POST /upload-excel-and-generate` - Generate certificates from Excel
- `POST /send-certificates` - Distribute certificates to students

See [backend/README.md](backend/README.md) for complete API documentation.

## Environment Variables

See `.env.example` for required environment variables:

- `SMTP_HOST` - SMTP server hostname
- `SMTP_PORT` - SMTP server port
- `SMTP_USER` - SMTP username
- `SMTP_PASS` - SMTP password
- `SMTP_USE_TLS` - Use TLS (True/False)
- `EMAIL_FROM` - From email address
- `ADMIN_EMAIL` - Admin email address
- `CORS_ORIGINS` - Allowed CORS origins (comma-separated)

## Development

### Backend Development

```bash
cd backend
python -m app.main
```

### Testing

```bash
cd backend
# Run tests (when implemented)
pytest
```

## Documentation

- [Backend README](backend/README.md) - Backend documentation
- [Backend Architecture](backend/ARCHITECTURE.md) - Architecture overview
- [Migration Guide](backend/MIGRATION.md) - Migration from N8N
- [Quick Start](backend/QUICKSTART.md) - Quick start guide

## License

[Add your license here]
