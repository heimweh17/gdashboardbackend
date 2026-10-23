FROM python:3.11-slim

# Refresh the system certificate store for outbound HTTPS.
RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Ensure logs are flushed
ENV PYTHONUNBUFFERED=1

# Start the API with Render's assigned port (or 10000 locally).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
