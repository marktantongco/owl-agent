# https_proxy_go — Go port of madeye/https_proxy

A from-scratch **Go** implementation of
[`madeye/https_proxy`](https://github.com/madeye/https_proxy) (originally Rust):
a stealth HTTPS forward proxy with automatic Let's Encrypt TLS, multi-user
basic auth, HTTP/2 CONNECT tunneling, and nginx-style camouflage.

## Why this port

The Rust original needs a Rust toolchain and is TLS-first (it requires a public
domain + port 443 for ACME). The Go port keeps feature parity and adds:

- **Plain HTTP proxy mode** — set `domain: ""` and it runs as a simple
  authenticated forward proxy on any port. Perfect for local/dev use, and how
  OWL-AGENT consumes it in the sandbox.
- A single static binary (`proxies/bin/https_proxy_go`) — no runtime deps.
- Interactive `setup` wizard instead of the TUI.

Not ported: systemd `install`/`uninstall` subcommands (upstream's TUI wizard is
replaced by interactive prompts). Everything else — CONNECT tunneling, HTTP
forwarding with header stripping, 407 auth gating, stealth nginx 404,
HTTP/2 (incl. extended CONNECT on Go 1.22+), ACME staging support, TCP Fast
Open — is implemented.

## Build

```bash
bash proxies/build.sh            # or: bash proxies/https_proxy_go/build.sh
```

Requires Go 1.22+.

Builds are version-stamped: `VERSION=… bash proxies/https_proxy_go/build.sh`
(defaults to nearest git tag, then `dev`). Check it with
`proxies/bin/https_proxy_go version`.

## Run

```bash
cp proxies/https_proxy_go/config.example.yaml config.yaml
# edit config.yaml (set domain for TLS mode, or leave it empty for plain HTTP)
proxies/bin/https_proxy_go run --config config.yaml
```

Try it:

```bash
# plain HTTP mode on 127.0.0.1:8080 — forward proxy through it:
curl --proxy http://alice:hunter2@127.0.0.1:8080 http://example.com/
# CONNECT tunnel:
curl --proxy http://alice:hunter2@127.0.0.1:8080 https://example.com/
# bad/absent credentials → 407:
curl -s -o /dev/null -w '%{http_code}\n' --proxy http://127.0.0.1:8080 http://example.com/
# direct probe → stealth nginx 404:
curl -i http://127.0.0.1:8080/ | head -5
```

## Wire into OWL-AGENT

```bash
export OWL_HTTPS_PROXY="https://alice:hunter2@proxy.example.com:443"  # or the plain-HTTP URL
bash run.sh server
```

Or list it alongside other proxies:

```bash
export OWL_EXTRA_PROXIES="https://alice:hunter2@proxy.example.com:443,socks5://127.0.0.1:42069"
bash run.sh server
```
