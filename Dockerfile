# Lantrn Agent Builder - Docker Configuration
# Optimized for Mac Ultra (ARM64) + NAS deployment

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.11-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install ".[dev]" || pip install -e .

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.11-slim-bookworm AS runtime

# Labels for container management
LABEL maintainer="Lantrn.ai <hello@lantrn.ai>" \
      version="0.1.0" \
      description="Lantrn Agent Builder - On-prem AI agent system" \
      architecture="arm64"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # Playwright configuration
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 \
    # ChromaDB configuration
    CHROMA_DB_PATH=/app/workspace/data/chromadb \
    # Application settings
    LANTRN_WORKSPACE=/app/workspace \
    LANTRN_LOG_LEVEL=INFO

# Install system dependencies for Playwright, ChromaDB, and document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential utilities
    curl \
    wget \
    gnupg \
    ca-certificates \
    # Playwright browser dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libpangocairo-1.0-0 \
    # Additional dependencies for document processing
    libxml2 \
    libxslt1.1 \
    # Fonts for browser rendering
    fonts-liberation \
    fonts-noto-color-emoji \
    # SQLite for ChromaDB
    sqlite3 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create application directories
WORKDIR /app
RUN mkdir -p /app/workspace \
    /app/workspace/.bmad/profiles \
    /app/workspace/.bmad/blueprints \
    /app/workspace/.bmad/runs \
    /app/workspace/agents \
    /app/workspace/policies \
    /app/workspace/logs \
    /app/workspace/data/chromadb \
    /app/workspace/config \
    /ms-playwright

# Copy application source
COPY src/ /app/src/
COPY pyproject.toml /app/
COPY README.md /app/

# Install the package
RUN pip install -e ".[dev]"

# Install Playwright browsers (Chromium for ARM64)
RUN playwright install chromium --with-deps

# Copy default configuration files
COPY policies/ /app/workspace/policies/
COPY agents/ /app/workspace/agents/
COPY .bmad/profiles/ /app/workspace/.bmad/profiles/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash lantrn \
    && chown -R lantrn:lantrn /app /ms-playwright

# Switch to non-root user
USER lantrn

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Entrypoint script
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
USER root
RUN chmod +x /app/docker/entrypoint.sh
USER lantrn

# Default command
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "lantrn_agent.api:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
