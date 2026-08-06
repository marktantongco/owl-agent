# prox5 — SOCKS5 server wrapper for OWL-AGENT

Thin Go wrapper around [`yunginnanet/prox5`](https://github.com/yunginnanet/prox5):
it validates a pool of upstream proxies and exposes them as **one local SOCKS5
server that rotates through the pool on every connection**.

## Build

```bash
bash proxies/build.sh          # or: bash proxies/prox5/build.sh
```

Requires Go 1.21+ (not bundled with the Freebuff sandbox — build on your machine
or CI).

## Run

```bash
bash run.sh prox5 -listen 127.0.0.1:42069 -file proxies.txt
```

- `-file` — plain-text list of upstream proxies, one per line
  (`http://`, `https://`, `socks4://`, `socks5://`). prox5 validates them and
  keeps only working endpoints.
- `-listen` — SOCKS5 bind address (default `127.0.0.1:42069`).

## Wire into OWL-AGENT

```bash
export OWL_PROX5_SOCKS5="127.0.0.1:42069"   # or the full socks5:// URL
bash run.sh server
```

Or skip the env var and pass the flag directly:

```bash
bash run.sh server --extra-proxies "socks5://127.0.0.1:42069"
```

Verify with `curl --socks5 127.0.0.1:42069 https://httpbin.org/ip`, then
`POST /fetch` on the OWL-AGENT API will route through the prox5 pool.
