# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and browsers
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps

COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

COPY . .

RUN mkdir -p logs data config

RUN groupadd -r parseruser && useradd -r -g parseruser parseruser
RUN chown -R parseruser:parseruser /app

USER parseruser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOME=/app

EXPOSE 8000

CMD ["python", "-m", "src.main"]