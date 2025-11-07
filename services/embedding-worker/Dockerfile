FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Using CPU-only torch to reduce image size
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

# Pre-download the model during build to avoid runtime download
RUN python -c "from sentence_transformers import SentenceTransformer; \
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
    print(f'Model cached, dimension: {model.get_sentence_embedding_dimension()}')"

# Copy application code
COPY embedding_worker.py .

# Create non-root user for security
RUN useradd -m -u 1000 worker && chown -R worker:worker /app
USER worker

# Set Python to run unbuffered for better logging
ENV PYTHONUNBUFFERED=1

# Health check (optional - requires health endpoint implementation)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
#     CMD python -c "import sys; sys.exit(0)"

# Run the worker
CMD ["python", "embedding_worker.py"]