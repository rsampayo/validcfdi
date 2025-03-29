FROM python:3.9-slim

WORKDIR /app

# Install PostgreSQL client and dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# The API token should be set at runtime in production
ENV API_TOKEN=your-secret-token

# Command to run the application
CMD uvicorn main:app --host 0.0.0.0 --port $PORT 