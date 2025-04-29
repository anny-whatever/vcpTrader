FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by some Python packages
# Example: psycopg2 might need postgresql-client or libpq-dev
# Add other dependencies as needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

# Ensure the server listens on 0.0.0.0 to be accessible from outside the container
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 