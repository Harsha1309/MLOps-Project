FROM python:3.12-slim

WORKDIR /app

# Install system deps (kept minimal; add build-essential if a wheel needs compiling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY build_dataset.py train.py main.py test_api.py ./

# Build dataset and train the model at image build time
RUN python build_dataset.py && python train.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]