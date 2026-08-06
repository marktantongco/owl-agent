// owl-prox5 — thin OWL-AGENT wrapper around yunginnanet/prox5.
//
// Loads a validated proxy pool and exposes it as a single local SOCKS5 server
// that rotates through the pool on every connection. OWL-AGENT then uses this
// server as one (or more) pool entries via OWL_PROX5_SOCKS5 / OWL_EXTRA_PROXIES.
//
// Build: bash proxies/build.sh
// Run:   ./owl-prox5 -listen 127.0.0.1:42069 -file proxies.txt
package main

import (
	"bufio"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"git.tcp.direct/kayos/prox5"
)

// version is stamped at build time via -ldflags "-X main.version=...".
var version = "dev"

func main() {
	listen := flag.String("listen", "127.0.0.1:42069", "SOCKS5 listen address")
	file := flag.String("file", "", "text file with proxies, one per line (http/https/socks4/socks5)")
	showVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()

	if *showVersion {
		fmt.Printf("owl-prox5 %s\n", version)
		return
	}

	engine := prox5.NewProxyEngine()

	if *file != "" {
		f, err := os.Open(*file)
		if err != nil {
			log.Fatalf("open proxy file: %v", err)
		}
		defer f.Close()

		loaded := 0
		sc := bufio.NewScanner(f)
		for sc.Scan() {
			line := sc.Text()
			if line == "" {
				continue
			}
			if engine.LoadSingleProxy(line) {
				loaded++
			}
		}
		if err := sc.Err(); err != nil {
			log.Fatalf("read proxy file: %v", err)
		}
		log.Printf("loaded %d proxies from %s", loaded, *file)
	}

	if err := engine.Start(); err != nil {
		log.Fatalf("engine start: %v", err)
	}

	go func() {
		if err := engine.StartSOCKS5Server(*listen, "", ""); err != nil {
			log.Fatalf("socks5 server: %v", err)
		}
	}()

	log.Printf("owl-prox5 %s — SOCKS5 rotating proxy server on %s", version, *listen)
	log.Printf("test: curl --socks5 %s https://httpbin.org/ip", *listen)

	// Block until SIGINT/SIGTERM.
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Println("shutting down")
}
