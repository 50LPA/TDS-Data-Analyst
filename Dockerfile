FROM python:3.11-slim

# Prevent Python from writing pyc files & buffering output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory inside container
WORKDIR /app

# Copy requirements first (caching optimization)
COPY requirements.txt .

# Install Python dependencies inside the image
RUN pip install --no-cache-dir -r requirements.txt

# Command will be overridden when running the container
CMD ["python3"]
