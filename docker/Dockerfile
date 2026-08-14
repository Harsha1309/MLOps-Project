FROM python:3.12-slim

WORKDIR /app

# Install system deps (kept minimal; add build-essential if a wheel needs compiling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer caching)
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code and install it as a package
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Build dataset and train the model at image build time
RUN python src/tourism_api/pipeline/build_dataset.py && python src/tourism_api/pipeline/train.py

EXPOSE 8000

CMD ["uvicorn", "tourism_api.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
