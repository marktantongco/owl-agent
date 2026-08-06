# https_proxy — stealth forward proxy for OWL-AGENT

Build + run tooling for [`madeye/https_proxy`](https://github.com/madeye/https_proxy),
a **Rust** stealth HTTPS forward proxy: automatic Let's Encrypt TLS (ACME
TLS-ALPN-01 on port 443), multi-user basic auth, HTTP/2 + CONNECT tunneling, and
nginx-style 404 camouflage against scanners.

## Build

```bash
bash proxies/build.sh          # or: bash proxies/https_proxy/build.sh
```

Requires Rust 1.70+ (not bundled with the Freebuff sandbox — build on a machine
with a public IP + DNS record, or CI).

## Run

```bash
cp proxies/https_proxy/config.example.yaml proxies/https_proxy/config.yaml
# edit: listen, domain (DNS A record → this host), acme.email, users
proxies/bin/https_proxy run --config proxies/https_proxy/config.yaml
```

The proxy listens on `0.0.0.0:443` and auto-issues its TLS certificate. It's
**TLS-first**: it needs a public domain and outbound 443 access to Let's Encrypt.
For local/dev testing without a public domain, use prox5 (SOCKS5) instead.

## Wire into OWL-AGENT

```bash
export OWL_HTTPS_PROXY="https://alice:hunter2@proxy.example.com:443"
bash run.sh server
```

Or add it alongside other proxies:

```bash
export OWL_EXTRA_PROXIES="https://alice:hunter2@proxy.example.com:443,socks5://127.0.0.1:42069"
bash run.sh server
```

Authenticated HTTPS URLs work directly as httpx/curl_cffi proxy URLs, so the
pool will route HTTPS traffic through this proxy via CONNECT tunneling.
