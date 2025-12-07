# Architecture Overview

## Design Principles

1. **Modular Architecture**: Clear separation of concerns with distinct layers
2. **SSOT (Single Source of Truth)**: Configuration centralized in `core/config.py`
3. **Clean Separation**: API routes, services, utilities, and models are separate
4. **Extensive Logging**: All operations logged with context
5. **Strong Error Handling**: Comprehensive try/except blocks with clear messages
6. **Production-Ready**: Proper file handling, validation, and error recovery

## Directory Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── api/                       # API route handlers (presentation layer)
│   │   ├── template_routes.py    # Template management endpoints
│   │   ├── certificate_routes.py # Certificate generation endpoints
│   │   └── distribution_routes.py # Distribution endpoints
│   ├── core/                      # Core configuration (SSOT)
│   │   ├── config.py             # Application settings
│   │   └── logging_config.py     # Logging setup
│   ├── services/                  # Business logic (service layer)
│   │   ├── excel_parser.py       # Excel parsing service
│   │   ├── certificate_generator.py # PDF generation service
│   │   ├── email_service.py      # SMTP email service
│   │   └── distributor.py        # Certificate distribution service
│   ├── utils/                     # Utility functions
│   │   ├── zip_utils.py          # ZIP file operations
│   │   ├── file_utils.py         # File handling utilities
│   │   └── text_utils.py         # Text processing (RTL, sanitization)
│   └── models/                    # Pydantic models (data validation)
│       ├── student_model.py      # Student data model
│       ├── batch_request.py      # Batch request models
│       └── distribution_result.py # Distribution result models
├── data/                          # Data directory (templates stored here)
├── logs/                          # Log files
├── fonts/                         # Font files
├── fields_config.json            # Certificate field configuration
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
└── README.md                     # Documentation
```

## Layer Responsibilities

### API Layer (`app/api/`)
- Handle HTTP requests/responses
- Validate input (file types, parameters)
- Call appropriate services
- Return formatted responses
- **No business logic** - delegates to services

### Service Layer (`app/services/`)
- Implement business logic
- Coordinate between utilities
- Handle service-specific errors
- Log operations
- **No HTTP concerns** - pure Python logic

### Utility Layer (`app/utils/`)
- Reusable helper functions
- File operations
- Text processing
- ZIP operations
- **No business logic** - pure utilities

### Model Layer (`app/models/`)
- Pydantic models for validation
- Data structure definitions
- Type safety
- **No logic** - data structures only

### Core Layer (`app/core/`)
- Configuration management (SSOT)
- Logging setup
- Environment variable handling
- **Singleton pattern** for settings

## Data Flow

### Certificate Generation Flow

```
1. Client → API Route (certificate_routes.py)
   ↓
2. API Route → ExcelParser.parse_students()
   ↓
3. ExcelParser → Returns List[Student]
   ↓
4. API Route → CertificateGenerator.create_batch()
   ↓
5. CertificateGenerator → For each student:
   - Load template (file_utils)
   - Render fields (text_utils for RTL)
   - Generate PDF
   ↓
6. API Route → ZipUtils.build_zip()
   ↓
7. API Route → EmailService.send_zip_to_admin() (optional)
   ↓
8. API Route → Return ZIP file to client
```

### Distribution Flow

```
1. Client → API Route (distribution_routes.py)
   ↓
2. API Route → Distributor.process()
   ↓
3. Distributor → ExcelParser.parse_students()
   ↓
4. Distributor → ZipUtils.extract_zip()
   ↓
5. Distributor → Match students with PDFs by ID
   ↓
6. Distributor → Return List[DistributionResult]
   ↓
7. API Route → EmailService.send_certificate() (if requested)
   ↓
8. API Route → Return distribution results
```

## Key Design Patterns

### 1. Service Pattern
Each service is a class with clear responsibilities:
- `ExcelParser`: Parse Excel files
- `CertificateGenerator`: Generate PDFs
- `EmailService`: Send emails
- `Distributor`: Coordinate distribution

### 2. Utility Pattern
Stateless utility functions/classes:
- `ZipUtils`: ZIP operations
- `file_utils`: File operations
- `text_utils`: Text processing

### 3. Configuration Pattern (SSOT)
Single source of truth in `core/config.py`:
- All settings loaded from environment variables
- Centralized path management
- Consistent configuration access

### 4. Logging Pattern
Structured logging throughout:
- Logger initialized in `core/logging_config.py`
- All services use same logger
- Consistent log format
- File + console output

## Error Handling Strategy

1. **Validation Errors**: Caught at API layer, return 400
2. **Business Logic Errors**: Caught at service layer, logged, return 500
3. **File Errors**: Caught with specific error messages
4. **Email Errors**: Logged but don't fail the request (optional operation)

## Logging Strategy

All operations log:
- **INFO**: Normal operations (uploads, generations, sends)
- **WARNING**: Recoverable issues (missing fields, font fallbacks)
- **ERROR**: Failures (file errors, generation failures)
- **DEBUG**: Detailed information (file sizes, parsing details)

Log file: `/logs/backend.log`

## Extension Points

### Adding New Fields
1. Update `fields_config.json`
2. Update `Student` model if needed
3. No code changes required (field rendering is dynamic)

### Adding New Services
1. Create service class in `app/services/`
2. Add to API route if needed
3. Follow existing service patterns

### Adding New Endpoints
1. Add route handler in appropriate `app/api/*_routes.py`
2. Use existing services
3. Follow existing route patterns

## Testing Strategy

1. **Unit Tests**: Test services independently
2. **Integration Tests**: Test API endpoints
3. **E2E Tests**: Test full workflows

## Performance Considerations

1. **Binary Search**: Font sizing uses binary search (O(log N))
2. **Caching**: Fields config cached (LRU cache)
3. **Streaming**: Large files streamed, not loaded into memory
4. **Batch Processing**: Certificates generated in batch

## Security Considerations

1. **File Validation**: All uploaded files validated
2. **Filename Sanitization**: Filenames sanitized before use
3. **SMTP Credentials**: Stored in environment variables
4. **CORS**: Configurable CORS origins
5. **Input Validation**: Pydantic models validate all inputs

