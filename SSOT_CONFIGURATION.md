# Single Source of Truth (SSOT) Configuration

## Overview

The **FRONTEND_URL** is defined in **ONE place only** and used across the entire application.

## SSOT Location

**Backend Environment Variable: `FRONTEND_URL`**

- **Development**: Set in `docker-compose.yml` or `.env` file
- **Production**: Set in `docker-compose.prod.yml` or production `.env` file

## How It Works

### 1. Backend Configuration (SSOT)

The backend reads `FRONTEND_URL` from environment variables:

```yaml
# docker-compose.prod.yml
environment:
  - FRONTEND_URL=https://jabanes.github.io/Auto-Certificate-Frontend/
```

### 2. Backend Uses SSOT For:

- **CORS Configuration**: Automatically uses `FRONTEND_URL` for allowed origins
- **Health Endpoint**: Returns `FRONTEND_URL` in `/health` response
- **All Backend References**: Any backend code that needs frontend URL uses `settings.FRONTEND_URL`

### 3. Frontend Gets SSOT From Backend

The frontend loads `FRONTEND_URL` from the backend `/health` endpoint:

```javascript
// Frontend automatically loads FRONTEND_URL from backend
const healthData = await fetch(`${API_BASE_URL}/health`).then(r => r.json());
const frontendUrl = healthData.frontend_url; // SSOT from backend
```

## Configuration Files

### Production (`docker-compose.prod.yml`)

```yaml
environment:
  # SSOT: Define FRONTEND_URL here - used everywhere
  - FRONTEND_URL=${FRONTEND_URL:-https://jabanes.github.io/Auto-Certificate-Frontend/}
```

### Development (`docker-compose.yml`)

```yaml
environment:
  # SSOT: Define FRONTEND_URL here - used everywhere
  - FRONTEND_URL=${FRONTEND_URL:-http://localhost:5501}
```

### Environment File (`.env`)

```env
# SSOT: Single Source of Truth for Frontend URL
FRONTEND_URL=https://jabanes.github.io/Auto-Certificate-Frontend/
```

## Benefits

1. ✅ **One Place to Update**: Change `FRONTEND_URL` in one place, affects entire app
2. ✅ **Automatic CORS**: Backend automatically allows the frontend URL
3. ✅ **Consistency**: Frontend and backend always use the same URL
4. ✅ **No Duplication**: No need to update multiple config files

## Usage

### Setting FRONTEND_URL

**Production:**
```bash
export FRONTEND_URL=https://jabanes.github.io/Auto-Certificate-Frontend/
docker-compose -f docker-compose.prod.yml up -d
```

**Development:**
```bash
export FRONTEND_URL=http://localhost:5501
docker-compose up -d
```

### Verifying SSOT

Check backend `/health` endpoint:
```bash
curl http://localhost:8000/health
```

Response includes:
```json
{
  "status": "ok",
  "frontend_url": "https://jabanes.github.io/Auto-Certificate-Frontend/",
  "cors_origins": ["https://jabanes.github.io/Auto-Certificate-Frontend/"]
}
```

## Important Notes

1. **CORS_ORIGINS**: If not explicitly set, automatically uses `FRONTEND_URL`
2. **Frontend Config**: Frontend `config.js` only defines `API_BASE_URL`, not `FRONTEND_URL`
3. **HTTPS Required**: Production frontend URL must use HTTPS (GitHub Pages)
4. **Backend HTTPS**: Production backend must also use HTTPS to avoid mixed content errors

