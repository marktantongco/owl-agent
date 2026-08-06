package main

import (
	"bufio"
	"encoding/base64"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func testProxy(cfg *Config) *ProxyServer {
	if cfg == nil {
		cfg = &Config{Listen: "127.0.0.1:0"}
	}
	if cfg.Stealth.ServerName == "" {
		cfg.Stealth.ServerName = "nginx/1.24.0"
	}
	return newProxyServer(cfg)
}

func basicAuth(user, pass string) string {
	return "Basic " + base64.StdEncoding.EncodeToString([]byte(user+":"+pass))
}

// ─── Config loading ─────────────────────────────────────────────

func TestLoadConfigDefaults(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.yaml")
	if err := os.WriteFile(path, []byte(
		"users:\n  - username: alice\n    password: hunter2\n",
	), 0o600); err != nil {
		t.Fatal(err)
	}
	cfg, err := loadConfig(path)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Listen != "0.0.0.0:443" {
		t.Fatalf("want default listen, got %q", cfg.Listen)
	}
	if cfg.Stealth.ServerName != "nginx/1.24.0" {
		t.Fatalf("want default server_name, got %q", cfg.Stealth.ServerName)
	}
	if len(cfg.Users) != 1 {
		t.Fatalf("want 1 user, got %d", len(cfg.Users))
	}
}

// ─── Stealth 404 ────────────────────────────────────────────────

func TestStealth404(t *testing.T) {
	p := testProxy(&Config{Stealth: StealthConfig{ServerName: "nginx/1.24.0"}})
	srv := httptest.NewServer(http.HandlerFunc(p.serveHTTP))
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("want 404, got %d", resp.StatusCode)
	}
	if got := resp.Header.Get("Server"); got != "nginx/1.24.0" {
		t.Fatalf("want nginx server header, got %q", got)
	}
	body, _ := io.ReadAll(resp.Body)
	if !strings.Contains(string(body), "404 Not Found") {
		t.Fatalf("body missing 404 marker: %q", body)
	}
}

func TestStealth404ForNonProxyPaths(t *testing.T) {
	p := testProxy(nil)
	req := httptest.NewRequest("GET", "/index.html", nil)
	w := httptest.NewRecorder()
	p.serveHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("want 404, got %d", w.Code)
	}
}

// ─── Auth gating ────────────────────────────────────────────────

func TestAuthMissingCredentials(t *testing.T) {
	p := testProxy(&Config{Users: []User{{Username: "alice", Password: "hunter2"}}})
	req := httptest.NewRequest("GET", "http://example.com/x", nil)
	w := httptest.NewRecorder()
	p.serveHTTP(w, req)
	if w.Code != http.StatusProxyAuthRequired {
		t.Fatalf("want 407, got %d", w.Code)
	}
	if w.Header().Get("Proxy-Authenticate") == "" {
		t.Fatal("want Proxy-Authenticate header on 407")
	}
}

func TestAuthBadCredentials(t *testing.T) {
	p := testProxy(&Config{Users: []User{{Username: "alice", Password: "hunter2"}}})
	for _, creds := range [][2]string{
		{"alice", "wrong"},
		{"bob", "hunter2"},
		{"alice", ""},
	} {
		req := httptest.NewRequest("GET", "http://example.com/x", nil)
		req.Header.Set("Proxy-Authorization", basicAuth(creds[0], creds[1]))
		w := httptest.NewRecorder()
		p.serveHTTP(w, req)
		if w.Code != http.StatusProxyAuthRequired {
			t.Fatalf("creds %q should be rejected, got %d", creds, w.Code)
		}
	}
}

func TestAuthMalformedHeader(t *testing.T) {
	p := testProxy(&Config{Users: []User{{Username: "alice", Password: "hunter2"}}})
	req := httptest.NewRequest("GET", "http://example.com/x", nil)
	req.Header.Set("Proxy-Authorization", "Basic !!!not-base64!!!")
	w := httptest.NewRecorder()
	p.serveHTTP(w, req)
	if w.Code != http.StatusProxyAuthRequired {
		t.Fatalf("want 407, got %d", w.Code)
	}
}

func TestConnectRequiresAuth(t *testing.T) {
	p := testProxy(&Config{Users: []User{{Username: "alice", Password: "hunter2"}}})
	req := httptest.NewRequest(http.MethodConnect, "http://example.com:443", nil)
	w := httptest.NewRecorder()
	p.serveHTTP(w, req)
	if w.Code != http.StatusProxyAuthRequired {
		t.Fatalf("want 407, got %d", w.Code)
	}
}

// ─── HTTP forwarding ────────────────────────────────────────────

func TestForwardingWithAuth(t *testing.T) {
	var leakedProxyAuth, leakedProxyConn string
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		leakedProxyAuth = r.Header.Get("Proxy-Authorization")
		leakedProxyConn = r.Header.Get("Proxy-Connection")
		w.Header().Set("X-Upstream", "yes")
		_, _ = w.Write([]byte("forwarded-ok"))
	}))
	defer upstream.Close()

	p := testProxy(&Config{Users: []User{{Username: "alice", Password: "hunter2"}}})
	req := httptest.NewRequest("GET", upstream.URL+"/path?q=1", nil)
	req.Header.Set("Proxy-Authorization", basicAuth("alice", "hunter2"))
	req.Header.Set("Proxy-Connection", "keep-alive")
	w := httptest.NewRecorder()
	p.serveHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("want 200, got %d (%s)", w.Code, w.Body.String())
	}
	if body := w.Body.String(); body != "forwarded-ok" {
		t.Fatalf("unexpected body %q", body)
	}
	if w.Header().Get("X-Upstream") != "yes" {
		t.Fatal("upstream response header not copied")
	}
	if leakedProxyAuth != "" {
		t.Fatalf("Proxy-Authorization leaked upstream: %q", leakedProxyAuth)
	}
	if leakedProxyConn != "" {
		t.Fatalf("Proxy-Connection leaked upstream: %q", leakedProxyConn)
	}
}

func TestForwardingOpenProxyWhenNoUsers(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("open-ok"))
	}))
	defer upstream.Close()

	p := testProxy(nil) // no users → open proxy
	req := httptest.NewRequest("GET", upstream.URL+"/", nil)
	w := httptest.NewRecorder()
	p.serveHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", w.Code)
	}
	if w.Body.String() != "open-ok" {
		t.Fatalf("unexpected body %q", w.Body.String())
	}
}

// ─── CONNECT tunneling ──────────────────────────────────────────

func TestConnectTunnel(t *testing.T) {
	// Raw TCP "target" that reads a single chunk and reports it back.
	target, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer target.Close()

	received := make(chan string, 1)
	go func() {
		conn, err := target.Accept()
		if err != nil {
			return
		}
		defer conn.Close()
		buf := make([]byte, 1024)
		n, _ := conn.Read(buf)
		received <- string(buf[:n])
	}()

	p := testProxy(&Config{Users: []User{{Username: "alice", Password: "hunter2"}}})
	srv := httptest.NewServer(http.HandlerFunc(p.serveHTTP))
	defer srv.Close()

	proxyAddr := strings.TrimPrefix(srv.URL, "http://")
	conn, err := net.Dial("tcp", proxyAddr)
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()

	targetAddr := target.Addr().String()
	req := "CONNECT " + targetAddr + " HTTP/1.1\r\n" +
		"Host: " + targetAddr + "\r\n" +
		"Proxy-Authorization: " + basicAuth("alice", "hunter2") + "\r\n\r\n"
	if _, err := conn.Write([]byte(req)); err != nil {
		t.Fatal(err)
	}

	br := bufio.NewReader(conn)
	statusLine, err := br.ReadString('\n')
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(statusLine, "200 Connection Established") {
		t.Fatalf("unexpected CONNECT response: %q", statusLine)
	}

	// Payload sent after the 200 goes straight through the tunnel.
	if _, err := conn.Write([]byte("hello-through-tunnel")); err != nil {
		t.Fatal(err)
	}
	select {
	case got := <-received:
		if got != "hello-through-tunnel" {
			t.Fatalf("target received %q, want %q", got, "hello-through-tunnel")
		}
	case <-time.After(5 * time.Second):
		t.Fatal("target never received tunneled payload")
	}
}
