FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# +++ PDF: add runtime libs required by WeasyPrint (Cairo/Pango/font stack) +++
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libharfbuzz0b \
    libfreetype6 \
    libfontconfig1 \
    libjpeg62-turbo \
    libpng16-16 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
# +++ end PDF deps +++

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# (optional but helpful): make sure Python can import 'agents'/'utils'
ENV PYTHONPATH=/app

# Ensure uploads dir exists for generated PDFs (safe no-op if created at runtime)
RUN mkdir -p /app/uploads

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
