# ═══════════════════════════════════════════════════════════
# OWL-AGENT Unified Synergy Gateway — Docker Image
# Multi-stage: Python runtime + OWL scripts
# ═══════════════════════════════════════════════════════════

# ── Stage 1: Base Python runtime ──────────────────────────
FROM python:3.12-slim AS base

LABEL org.opencontainers.image.title="OWL-AGENT Unified Synergy Gateway"
LABEL org.opencontainers.image.description="Unified free-tier AI proxy stack — forward proxy, resilient HTTP client, MCP server"
LABEL org.opencontainers.image.version="6.0.0"
LABEL org.opencontainers.image.source="https://github.com/owl-agent"

# Prevent Python buffering & ensure UTF-8
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip install --no-cache-dir aiohttp==3.11.14 httpx==0.28.1

# ── Stage 2: Application ──────────────────────────────────
FROM base AS app

# Create non-root user
RUN groupadd -r owl && useradd -r -g owl -d /app -s /sbin/nologin owl

# App directory structure
WORKDIR /app
RUN mkdir -p /app/scripts /app/config /app/logs && chown -R owl:owl /app

# Copy scripts
COPY scripts/forward_proxy.py         /app/scripts/
COPY scripts/proxy_defense_fixed_v3.py /app/scripts/
COPY scripts/owl_resilient_mcp.py      /app/scripts/

# Copy default configs
COPY config/proxy_pool.json     /app/config/
COPY config/proxy_sources.json  /app/config/

# Copy entrypoint
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Ensure scripts are executable
RUN chmod +x /app/scripts/*.py

# Switch to non-root
USER owl

# Default environment
ENV FORWARD_PROXY_PORT=60000 \
    UPSTREAM_PROXY="" \
    BYPASS_DOMAINS="nvidia.com,opencode.ai,amazonaws.com,kiro.dev" \
    PROXY_POOL_CONFIG="/app/config/proxy_pool.json" \
    PROXY_SOURCES_CONFIG="/app/config/proxy_sources.json" \
    OWL_ENRICH_ENABLED="" \
    CACHE_TTL=300 \
    CIRCUIT_BREAKER_THRESHOLD=3 \
    CIRCUIT_BREAKER_RECOVERY=60 \
    LOG_LEVEL=INFO \
    MCP_TRANSPORT=stdio

# Health check — forward proxy
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:${FORWARD_PROXY_PORT}/health || exit 1

# Expose ports
EXPOSE 60000 8333

# Volumes for config persistence & logs
VOLUME ["/app/config", "/app/logs"]

# Entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default: run all services
CMD ["all"]
