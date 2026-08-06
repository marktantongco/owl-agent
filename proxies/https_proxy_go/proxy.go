package main

import (
	"context"
	"crypto/subtle"
	"crypto/tls"
	"encoding/base64"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"strings"
	"syscall"
	"time"

	"golang.org/x/crypto/acme"
	"golang.org/x/crypto/acme/autocert"
	"golang.org/x/sys/unix"
)

// ProxyServer implements the stealth forward proxy.
type ProxyServer struct {
	cfg   *Config
	users map[string]string
}

func newProxyServer(cfg *Config) *ProxyServer {
	users := make(map[string]string, len(cfg.Users))
	for _, u := range cfg.Users {
		users[u.Username] = u.Password
	}
	return &ProxyServer{cfg: cfg, users: users}
}

// serveHTTP is the entry point for every request. Genuine proxy requests are
// CONNECT (tunneling) or absolute-URI HTTP; anything else is treated as a
// scanner/probe and gets a fake nginx 404.
func (p *ProxyServer) serveHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodConnect && !r.URL.IsAbs() {
		p.stealth404(w, r)
		return
	}
	if !p.authorized(r) {
		w.Header().Set("Proxy-Authenticate", `Basic realm="owl-https-proxy"`)
		http.Error(w, "Proxy Authentication Required", http.StatusProxyAuthRequired)
		return
	}
	switch r.Method {
	case http.MethodConnect:
		p.handleConnect(w, r)
	default:
		p.handleHTTP(w, r)
	}
}

// authorized validates Proxy-Authorization against the configured users.
// With no users configured the proxy is open (same behaviour as upstream).
func (p *ProxyServer) authorized(r *http.Request) bool {
	if len(p.users) == 0 {
		return true
	}
	auth := r.Header.Get("Proxy-Authorization")
	if !strings.HasPrefix(auth, "Basic ") {
		return false
	}
	raw, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(auth, "Basic "))
	if err != nil {
		return false
	}
	user, pass, ok := strings.Cut(string(raw), ":")
	if !ok {
		return false
	}
	want, found := p.users[user]
	if !found {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(want), []byte(pass)) == 1
}

// stealth404 replies with an nginx-looking 404 to non-proxy traffic so the
// server looks like a boring web server to scanners.
func (p *ProxyServer) stealth404(w http.ResponseWriter, r *http.Request) {
	server := p.cfg.Stealth.ServerName
	log.Printf("stealth 404: %s %s (%s)", r.Method, r.URL.Path, r.RemoteAddr)
	w.Header().Set("Server", server)
	w.Header().Set("Content-Type", "text/html")
	w.WriteHeader(http.StatusNotFound)
	fmt.Fprintf(w, "<html>\r\n<head><title>404 Not Found</title></head>\r\n<body>\r\n<center><h1>404 Not Found</h1></center>\r\n<hr><center>%s</center>\r\n</body>\r\n</html>\r\n", server)
}

// handleConnect tunnels a client connection to the target host (CONNECT).
func (p *ProxyServer) handleConnect(w http.ResponseWriter, r *http.Request) {
	addr := r.Host
	if !strings.Contains(addr, ":") {
		addr += ":443"
	}
	dialer := &net.Dialer{Timeout: 30 * time.Second}
	upstream, err := dialer.DialContext(r.Context(), "tcp", addr)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer upstream.Close()

	log.Printf("CONNECT %s (%s)", addr, r.RemoteAddr)

	// HTTP/1.x: hijack the connection and splice bytes both ways.
	if r.ProtoMajor == 1 {
		hj, ok := w.(http.Hijacker)
		if !ok {
			http.Error(w, "hijacking not supported", http.StatusInternalServerError)
			return
		}
		client, _, err := hj.Hijack()
		if err != nil {
			return
		}
		defer client.Close()
		if _, err := client.Write([]byte("HTTP/1.1 200 Connection Established\r\n\r\n")); err != nil {
			return
		}
		go copyBoth(upstream, client)
		copyBoth(client, upstream)
		return
	}

	// HTTP/2 extended CONNECT (RFC 8441, Go 1.22+): full-duplex stream.
	w.WriteHeader(http.StatusOK)
	if fl, ok := w.(http.Flusher); ok {
		fl.Flush()
	}
	done := make(chan struct{})
	go func() {
		_, _ = io.Copy(upstream, r.Body)
		close(done)
	}()
	_, _ = io.Copy(w, upstream)
	<-done
}

func copyBoth(dst io.Writer, src io.Reader) {
	buf := make([]byte, 32*1024)
	_, _ = io.CopyBuffer(dst, src, buf)
	if cw, ok := dst.(interface{ CloseWrite() error }); ok {
		_ = cw.CloseWrite()
	}
}

// handleHTTP forwards plain HTTP proxy requests (absolute-URI) upstream.
func (p *ProxyServer) handleHTTP(w http.ResponseWriter, r *http.Request) {
	outReq := r.Clone(r.Context())
	outReq.RequestURI = ""
	stripHopByHop(outReq.Header)

	transport := &http.Transport{
		Proxy:             nil,
		DialContext:       (&net.Dialer{Timeout: 30 * time.Second}).DialContext,
		DisableKeepAlives: true,
	}
	resp, err := transport.RoundTrip(outReq)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	log.Printf("HTTP %s %s -> %d", r.Method, outReq.URL.String(), resp.StatusCode)
	copyHeaders(w.Header(), resp.Header)
	w.WriteHeader(resp.StatusCode)
	_, _ = io.Copy(w, resp.Body)
}

// stripHopByHop removes proxy and hop-by-hop headers before forwarding.
func stripHopByHop(h http.Header) {
	for _, key := range []string{
		"Proxy-Authorization", "Proxy-Connection", "Connection",
		"Keep-Alive", "Proxy-Authenticate", "Te", "Trailer",
		"Transfer-Encoding", "Upgrade",
	} {
		h.Del(key)
	}
}

func copyHeaders(dst, src http.Header) {
	for k, vs := range src {
		for _, v := range vs {
			dst.Add(k, v)
		}
	}
}

// runServer loads the config and serves until SIGINT/SIGTERM.
func runServer(configPath string) error {
	cfg, err := loadConfig(configPath)
	if err != nil {
		return err
	}
	proxy := newProxyServer(cfg)

	srv := &http.Server{
		Addr:    cfg.Listen,
		Handler: http.HandlerFunc(proxy.serveHTTP),
		TLSConfig: &tls.Config{
			MinVersion: tls.VersionTLS12,
			NextProtos: []string{"h2", "http/1.1"},
		},
		ReadHeaderTimeout: 30 * time.Second,
	}

	if cfg.Domain != "" {
		acmeMgr := &autocert.Manager{
			Prompt:     autocert.AcceptTOS,
			HostPolicy: autocert.HostWhitelist(cfg.Domain),
			Email:      cfg.ACME.Email,
			Cache:      autocert.DirCache(cfg.ACME.CacheDir),
		}
		if cfg.ACME.Staging {
			acmeMgr.Client = &acme.Client{DirectoryURL: "https://acme-staging-v02.api.letsencrypt.org/directory"}
		}
		srv.TLSConfig.GetCertificate = acmeMgr.GetCertificate
	}

	ln, err := listenWithConfig(cfg)
	if err != nil {
		return err
	}

	go gracefulShutdown(srv)
	if cfg.Domain != "" {
		log.Printf("https_proxy_go: TLS proxy on %s (domain %s, %d user(s))",
			cfg.Listen, cfg.Domain, len(cfg.Users))
		return srv.ServeTLS(ln, "", "")
	}
	log.Printf("https_proxy_go: plain HTTP proxy on %s (%d user(s))", cfg.Listen, len(cfg.Users))
	return srv.Serve(ln)
}

func gracefulShutdown(srv *http.Server) {
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Println("shutting down…")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(ctx)
}

// listenWithConfig enables TCP Fast Open when requested (Linux/macOS only).
func listenWithConfig(cfg *Config) (net.Listener, error) {
	if !cfg.Stealth.FastOpen || (runtime.GOOS != "linux" && runtime.GOOS != "darwin") {
		return net.Listen("tcp", cfg.Listen)
	}
	lc := net.ListenConfig{}
	lc.Control = func(network, address string, c syscall.RawConn) error {
		var opErr error
		if err := c.Control(func(fd uintptr) {
			opErr = syscall.SetsockoptInt(int(fd), syscall.IPPROTO_TCP, unix.TCP_FASTOPEN, 5)
		}); err != nil {
			return err
		}
		return opErr
	}
	return lc.Listen(context.Background(), "tcp", cfg.Listen)
}
