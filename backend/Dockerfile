# Multi-stage build for smaller image size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy application code with correct permissions
COPY --chown=app:app . .

# Create uploads directory
RUN mkdir -p uploads && chown app:app uploads

# Switch to non-root user
USER app

# Set default port (Railway will override this)
ENV PORT=8000

# Expose port
EXPOSE $PORT

# Health check with dynamic port
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Run the application with proper port handling
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
# # backend/Dockerfile
# FROM python:3.11-slim

# # Set working directory
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     gcc \
#     g++ \
#     ffmpeg \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements and install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY . .

# # Create uploads directory
# RUN mkdir -p uploads

# # Expose port
# EXPOSE 8000

# # Health check
# HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8000/health || exit 1

# # Run the application
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

