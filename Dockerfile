FROM python:3.12-slim

# Prevent Python from writing .pyc files and force stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEEPFACE_HOME=/usr/src/app

WORKDIR /usr/src/app

# Install system dependencies required by OpenCV and DeepFace
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Handles large files and slow network issues by increasing the timeout
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Pre-download the FaceNet512 weights so the container starts up faster
RUN python -c "from deepface import DeepFace; DeepFace.build_model('Facenet512')"

# Copy the rest of the application code
COPY ./app ./app

# Create a non-root user and switch to it
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 --no-create-home appuser && \
    chown -R appuser:appgroup /usr/src/app

USER appuser

# Expose the port the FastAPI server runs on
EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]