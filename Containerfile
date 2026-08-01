# Containerfile for OWL-AGENT v4.2 — Podman-native
# Build: podman build -t owl-agent:4.2 -f Containerfile .
# Run:   podman run --rm -p 60000:60000 -p 9090:9090 owl-agent:4.2

FROM docker.io/library/python:3.11-slim

LABEL maintainer="owl-agent" \
      version="4.2" \
      description="OWL-AGENT self-optimising proxy HTTP client"

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 for agent-browser
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash owl
WORKDIR /home/owl

# Copy code
COPY --chown=owl:owl proxy_defense.py /home/owl/.owl-agent/proxy_defense.py
COPY --chown=owl:owl owl_server.py /home/owl/.owl-agent/owl_server.py
COPY --chown=owl:owl run.sh /home/owl/.owl-agent/run.sh

USER owl
WORKDIR /home/owl/.owl-agent

# Install Python deps
RUN python3 -m venv venv && \
    venv/bin/pip install --no-cache-dir --upgrade pip && \
    venv/bin/pip install --no-cache-dir \
        httpx[socks] aiohttp aiofiles \
        proxybroker2 resilient-httpx circuitbreaker curl_cffi \
        prometheus-client

# Install agent-browser
RUN npx --yes skills add vercel-labs/agent-browser 2>/dev/null || true

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

EXPOSE 60000 9091

ENTRYPOINT ["venv/bin/python", "owl_server.py"]
CMD ["--host", "0.0.0.0", "--api-port", "60000", "--metrics-port", "9091", "--countries", "US", "GB", "PH"]
