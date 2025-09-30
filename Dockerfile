# ---------- Stage 1: Builder ----------
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --upgrade pip

# Copy only requirements first (cache-friendly)
COPY requirements.txt .

# Install dependencies into a temp folder
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- Stage 2: Final Image ----------
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local


# Copy source code
COPY . .

# Default command for API service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
