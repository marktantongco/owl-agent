FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash owl
USER owl
WORKDIR /home/owl

# Install OWL-AGENT
RUN mkdir -p ~/.owl-agent/cache/http ~/.owl-agent/config
COPY --chown=owl:owl proxy_defense.py owl_agent_v4.py run.sh ~/.owl-agent/
RUN chmod +x ~/.owl-agent/run.sh

# Python venv + deps
RUN python3 -m venv ~/.owl-agent/venv && \
    ~/.owl-agent/venv/bin/pip install --upgrade pip && \
    ~/.owl-agent/venv/bin/pip install \
        httpx[socks] \
        aiohttp \
        aiofiles \
        proxybroker2 \
        litproxy \
        resilient-httpx \
        circuitbreaker \
        curl_cffi \
        redis \
        prometheus-client

EXPOSE 8000

ENTRYPOINT ["/home/owl/.owl-agent/run.sh"]
CMD ["--help"]
