# BASE STAGE
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Installing system dependecies for Cartopy, Shapely packages AND R scripting
RUN apt-get update && apt-get install -y \
    build-essential \
    libgeos-dev \
    libproj-dev \
    proj-data \
    proj-bin \
    r-base \
    r-cran-ggplot2 \
    r-cran-openxlsx \
    && rm -rf /var/lib/apt/lists/*

# Installing Python packages
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# DEVELOPMENT STAGE
FROM base AS development
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# PRODUCTION STAGE
FROM base AS production
COPY ./src ./src
COPY ./web ./web
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]