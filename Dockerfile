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

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps

COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

COPY . .

RUN mkdir -p logs data config \
    && mkdir -p src/parsers/egrul_working_dir \
    && mkdir -p src/parsers/ras_working_dir \
    && touch src/parsers/egrul_working_dir/.gitkeep \
    && touch src/parsers/ras_working_dir/.gitkeep

RUN groupadd -r parseruser && useradd -r -g parseruser parseruser
RUN chown -R parseruser:parseruser /app

USER parseruser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOME=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["python", "-m", "src.main", "--serve", "--host", "0.0.0.0", "--port", "8000"]