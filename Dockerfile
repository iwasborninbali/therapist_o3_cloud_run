FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json

# Expose the port
EXPOSE ${PORT}

# Start the application with uvicorn
CMD exec uvicorn bot.main:app --host 0.0.0.0 --port ${PORT} 