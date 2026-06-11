# ==========================================
# STAGE 1: Builder
# Used to compile heavy Python wheels with dev dependencies
# ==========================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Install compilers and development headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Generate pre-compiled wheels for all requirements
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# ==========================================
# STAGE 2: Base Runtime
# Minimal environment with runtime-only libraries
# ==========================================
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Install only the strictly required runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-c1v5 \
    proj-data \
    proj-bin \
    r-base-core \
    r-cran-ggplot2 \
    r-cran-openxlsx \
    && rm -rf /var/lib/apt/lists/*

# Copy and install pre-compiled wheels
COPY --from=builder /app/wheels /wheels
RUN pip install --upgrade pip \
    && pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

# ==========================================
# STAGE 3: Development Environment
# Used for local development with code mounting
# ==========================================
FROM base AS development
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# ==========================================
# STAGE 4: Production Environment
# Isolated, slim environment for deployment
# ==========================================
FROM base AS production
COPY ./src ./src
COPY ./web ./web
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]