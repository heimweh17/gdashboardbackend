FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Ensure logs are flushed
ENV PYTHONUNBUFFERED=1

# Start FastAPI app
CMD sh -c "uvicorn ${APP_MODULE} --host 0.0.0.0 --port 10000"
