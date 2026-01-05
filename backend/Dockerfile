FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
        wget \
        fonts-liberation \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpangocairo-1.0-0 \
        libpango-1.0-0 \
        libxcb1 \
        libx11-6 \
        libx11-xcb1 \
        libxext6 \
        libxfixes3 \
        libdrm2 \
        xvfb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]



