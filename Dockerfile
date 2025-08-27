# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY railway-requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r railway-requirements.txt

# Copy application files
COPY . .

# Create temp directory
RUN mkdir -p temp

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (not needed for bot but good practice)
EXPOSE 8000

# Run the bot
CMD ["python", "main.py"]