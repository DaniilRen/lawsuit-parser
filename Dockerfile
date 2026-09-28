FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --trusted-host pypi.tuna.tsinghua.edu.cn \
        -r requirements.txt

RUN /opt/venv/bin/playwright install chromium \
    && /opt/venv/bin/playwright install-deps || true

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOME=/app

COPY . .

RUN mkdir -p logs data \
    && mkdir -p src/parsers/egrul_working_dir \
    && mkdir -p src/parsers/ras_working_dir \
    && mkdir -p src/parsers/fedresurs_working_dir \
    && touch src/parsers/egrul_working_dir/.gitkeep \
    && touch src/parsers/ras_working_dir/.gitkeep \
    && touch src/parsers/fedresurs_working_dir/.gitkeep

RUN groupadd -r parseruser && useradd -r -g parseruser parseruser \
    && chown -R parseruser:parseruser /app /opt/venv

USER parseruser

EXPOSE 5050

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5050/api/v1/health || exit 1

CMD ["python", "-m", "src.main", "--serve", "--host", "0.0.0.0", "--port", "5050"]