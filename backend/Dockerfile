# ============================================================================
# Vayuntra Backend — Production Dockerfile
# Multi-stage build for minimal, hardened image
# ============================================================================

# ── Stage 1: Builder ─────────────────────────────────────────────────────
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into isolated layer
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim as runtime

LABEL org.opencontainers.image.title="Vayuntra Backend"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.vendor="Vayuntra"

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y

# Non-root user
RUN groupadd --gid 1000 vayuntra && \
    useradd --uid 1000 --gid 1000 --no-create-home --shell /sbin/nologin vayuntra

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY --chown=vayuntra:vayuntra app/ ./app/

# Create necessary directories with correct ownership
RUN mkdir -p /tmp /var/log/vayuntra && \
    chown -R vayuntra:vayuntra /var/log/vayuntra

# Security: remove write permission on app code
RUN chmod -R 550 /app

USER vayuntra

EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
