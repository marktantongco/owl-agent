// Command https_proxy_go is a Go port of madeye/https_proxy
// (https://github.com/madeye/https_proxy): a stealth HTTPS forward proxy
// with automatic Let's Encrypt TLS, multi-user basic auth, CONNECT
// tunneling, HTTP forwarding, and nginx-style camouflage against scanners.
package main

import (
	"fmt"
	"log"
	"os"
)

const version = "1.0.0"

func usage() {
	fmt.Fprintf(os.Stderr, `https_proxy_go %s — stealth HTTPS/HTTP forward proxy (Go port of madeye/https_proxy)

USAGE:
  https_proxy_go run     --config config.yaml   Start the proxy server (default)
  https_proxy_go setup                          Interactively generate config.yaml
  https_proxy_go help                            Show this help

CONFIG:
  cp config.example.yaml config.yaml && edit, then:
  https_proxy_go run --config config.yaml

FEATURES:
  • Automatic TLS via Let's Encrypt (ACME TLS-ALPN-01) when a domain is set
  • Plain HTTP proxy mode when no domain is set (great for local/dev)
  • Multi-user basic auth (407 + Proxy-Authenticate on bad credentials)
  • CONNECT tunneling for HTTPS, HTTP forwarding for http:// requests
  • Stealth: non-proxy requests get a fake nginx 404
  • HTTP/2, including extended CONNECT (RFC 8441) on Go 1.22+
`, version)
}

func main() {
	args := os.Args[1:]
	if len(args) == 0 {
		args = []string{"run"}
	}

	switch args[0] {
	case "run":
		configPath := "config.yaml"
		for i := 1; i < len(args); i++ {
			if args[i] == "--config" && i+1 < len(args) {
				configPath = args[i+1]
				i++
			}
		}
		if err := runServer(configPath); err != nil {
			log.Fatalf("server error: %v", err)
		}
	case "setup":
		if err := runSetup(); err != nil {
			log.Fatalf("setup error: %v", err)
		}
	case "help", "--help", "-h":
		usage()
	default:
		fmt.Fprintf(os.Stderr, "unknown command %q\n\n", args[0])
		usage()
		os.Exit(2)
	}
}
