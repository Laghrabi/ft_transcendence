FROM python:3.12-slim AS builder

WORKDIR /build

RUN	apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN mkdir -p /install && pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runner

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/false appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app

COPY . .

RUN chmod +x entrypoint.sh

# Collect Django static files (admin panel, swagger, etc.)
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Switch to non-root user for runtime
USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]