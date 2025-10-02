# Use official Python slim image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py extract_pptx_fields.py ./
COPY fields_config.json certificate-template.png ./

# Copy fonts into the image
COPY fonts ./fonts


# Expose FastAPI port
EXPOSE 8000

# Run server with uvicorn
CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8000"]
