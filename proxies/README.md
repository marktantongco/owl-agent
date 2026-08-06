# 🦉 OWL-AGENT Proxy Integrations

Self-hosted proxy servers that OWL-AGENT can treat as first-class pool entries.
Once built and running, wire them into the pool with env vars — no code changes needed.

| Project | Type | Language | Listen | Purpose |
|---|---|---|---|---|
| [**prox5**](https://github.com/yunginnanet/prox5) | SOCKS5/4/4a validating pool + SOCKS5 server | Go | `127.0.0.1:42069` | Run your own rotating SOCKS5 exit; great for local/dev use |
| [**https_proxy_go**](proxies/https_proxy_go/) | Stealth HTTPS/HTTP forward proxy (ACME TLS, basic auth, nginx camouflage) — **Go port** | Go | `0.0.0.0:443` (or plain HTTP mode) | Production-grade stealth proxy, single static binary |
| [**https_proxy**](https://github.com/madeye/https_proxy) | Stealth HTTPS forward proxy (upstream, Rust) | Rust | `0.0.0.0:443` | Upstream reference build (requires Rust toolchain) |

## Quick start

```bash
# 1. Build both (needs Go 1.21+ and Rust 1.70+ on your machine)
bash proxies/build.sh

# 2. Run prox5 (SOCKS5 on 127.0.0.1:42069)
bash run.sh prox5 -listen 127.0.0.1:42069 -file proxies.txt

# 3. Point OWL-AGENT at them
export OWL_PROX5_SOCKS5="127.0.0.1:42069"
export OWL_HTTPS_PROXY="https://alice:hunter2@proxy.example.com:443"
bash run.sh server
```

## Env vars

| Variable | Example | Effect |
|---|---|---|
| `OWL_EXTRA_PROXIES` | `socks5://127.0.0.1:42069,http://127.0.0.1:8080` | Comma-separated proxy URLs seeded into the pool |
| `OWL_PROX5_SOCKS5` | `127.0.0.1:42069` (or full `socks5://…` URL) | Convenience alias → adds a `socks5://` entry |
| `OWL_HTTPS_PROXY` | `https://user:pass@proxy.example.com:443` (or full URL) | Convenience alias → adds an `https://` entry |

All three merge into the `--extra-proxies` server flag, so you can also pass them
explicitly: `bash run.sh server --extra-proxies "socks5://127.0.0.1:42069"`.

Seeded proxies are always present in the pool (quality-scored like any other proxy),
so HTTPS URLs tunnel through them via CONNECT instead of falling back to direct.

## Notes

- The sandbox/preview image does **not** ship Go or Rust toolchains, so builds run
  on your own machine (or CI). The built binaries are meant to run alongside
  OWL-AGENT on the same host or a separate box.
- prox5 is a library; `proxies/prox5/main.go` is a thin wrapper that loads a proxy
  list from a file (one per line) and exposes a rotating SOCKS5 server. Feed it
  any mix of `http://`, `https://`, `socks4://`, `socks5://` endpoints.
- https_proxy is TLS-first (Let's Encrypt via ACME on port 443, needs a DNS record).
  For local testing without a public domain, prefer prox5.

## Module paths & versioning

- Each Go module carries its canonical path matching this repo
  (`github.com/marktantongco/owl-agent/proxies/prox5` and
  `github.com/marktantongco/owl-agent/proxies/https_proxy_go`).
- Binaries are version-stamped at build time. `VERSION` env wins over the
  nearest git tag (`git describe --tags`), which wins over `dev`:

  ```bash
  bash proxies/build.sh                      # stamps nearest git tag (or dev)
  VERSION=v0.4.5-test bash proxies/build.sh  # explicit version
  ```

- CI stamps tag builds with the tag name automatically
  (`github.ref_name` on `v*` pushes, commit SHA otherwise). Check a binary with
  `proxies/bin/https_proxy_go version` or `proxies/bin/owl-prox5 -version`.

## Canonical sources

The two Go projects are developed in their own public repositories; this tree
keeps working copies so the OWL-AGENT bundle stays self-contained:

- prox5 wrapper → <https://github.com/marktantongco/owl-prox5>
- https_proxy Go port → <https://github.com/marktantongco/owl-https-proxy>
