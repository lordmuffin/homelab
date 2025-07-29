FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make migrate.py executable
RUN chmod +x migrate.py

# Create directories for logs and reports
RUN mkdir -p /app/logs /app/reports

# Set up non-root user for security
RUN useradd --create-home --shell /bin/bash migrator && \
    chown -R migrator:migrator /app
USER migrator

# Set environment variables
ENV PYTHONPATH=/app/src
ENV LOG_FILE=/app/logs/migration.log
ENV SUCCESS_REPORT_FILE=/app/reports/migration_success.json
ENV ERROR_REPORT_FILE=/app/reports/migration_errors.json

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
ENTRYPOINT ["python", "migrate.py"]
CMD ["--help"]