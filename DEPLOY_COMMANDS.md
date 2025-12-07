# Docker Build, Tag, Push, and Deploy Commands

## Local Machine (Windows) - Build and Push

### 1. Navigate to Backend Directory
```bash
cd backend
```

### 2. Build Docker Image
```bash
docker build -t erez3535/cob-auto-certificates:v3 .
```

### 3. Tag as Latest (Optional)
```bash
docker tag erez3535/cob-auto-certificates:v3 erez3535/cob-auto-certificates:latest
```

### 4. Login to Docker Hub (if not already logged in)
```bash
docker login
```
Enter your Docker Hub credentials when prompted.

### 5. Push v3 to Docker Hub
```bash
docker push erez3535/cob-auto-certificates:v3
```

### 6. Push Latest Tag (Optional)
```bash
docker push erez3535/cob-auto-certificates:latest
```

### 7. Verify Push
Check Docker Hub: https://hub.docker.com/r/erez3535/cob-auto-certificates/tags

---

## VPS Server (Linux) - Pull and Deploy

### 1. SSH into VPS
```bash
ssh user@31.97.193.47
```

### 2. Navigate to Project Directory
```bash
cd /path/to/Auto-Certificate
```

### 3. Pull New Image
```bash
docker pull erez3535/cob-auto-certificates:v3
```

### 4. Update docker-compose.prod.yml (if needed)
Change image tag from `v2` to `v3`:
```yaml
image: erez3535/cob-auto-certificates:v3
```

### 5. Stop Current Containers
```bash
docker-compose -f docker-compose.prod.yml down
```

### 6. Start with New Image
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 7. Verify Deployment
```bash
# Check running containers
docker ps

# Check logs
docker logs certificate-backend

# Test health endpoint
curl http://localhost:8000/health
```

---

## One-Line Commands (Quick Reference)

### Local - Build and Push
```bash
cd backend && docker build -t erez3535/cob-auto-certificates:v3 . && docker push erez3535/cob-auto-certificates:v3
```

### VPS - Pull and Restart
```bash
docker pull erez3535/cob-auto-certificates:v3 && docker-compose -f docker-compose.prod.yml down && docker-compose -f docker-compose.prod.yml up -d
```

---

## Update docker-compose.prod.yml to Use v3

Before deploying, update the image tag:

```yaml
services:
  backend:
    image: erez3535/cob-auto-certificates:v3  # Changed from v2 to v3
```

