FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --trusted-host pypi.tuna.tsinghua.edu.cn \
        -r requirements.txt

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright

RUN /opt/venv/bin/playwright install chromium

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
    && chown -R parseruser:parseruser /app /opt/venv /opt/ms-playwright

USER parseruser

EXPOSE 5050

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5050/api/v1/health || exit 1

CMD ["python", "-m", "src.main", "--serve", "--host", "0.0.0.0", "--port", "5050"]