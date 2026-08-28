FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies for C extensions (Tree-sitter, asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy build config & install dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]"

# Copy source code and migrations
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY tests ./tests
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
