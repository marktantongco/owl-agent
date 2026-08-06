package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"gopkg.in/yaml.v3"
)

// Config mirrors the upstream madeye/https_proxy config.yaml schema.
type Config struct {
	Listen  string        `yaml:"listen"`
	Domain  string        `yaml:"domain"`
	ACME    ACMEConfig    `yaml:"acme"`
	Users   []User        `yaml:"users"`
	Stealth StealthConfig `yaml:"stealth"`
}

type ACMEConfig struct {
	Email    string `yaml:"email"`
	Staging  bool   `yaml:"staging"`
	CacheDir string `yaml:"cache_dir"`
}

type User struct {
	Username string `yaml:"username"`
	Password string `yaml:"password"`
}

type StealthConfig struct {
	ServerName string `yaml:"server_name"`
	FastOpen   bool   `yaml:"fast_open"`
}

// loadConfig reads and validates a YAML config file.
func loadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}
	if cfg.Listen == "" {
		cfg.Listen = "0.0.0.0:443"
	}
	if cfg.Stealth.ServerName == "" {
		cfg.Stealth.ServerName = "nginx/1.24.0"
	}
	return &cfg, nil
}

// runSetup interactively generates config.yaml (the Go equivalent of the
// upstream `https_proxy setup` TUI wizard).
func runSetup() error {
	reader := bufio.NewReader(os.Stdin)
	ask := func(prompt, def string) string {
		if def != "" {
			fmt.Printf("%s [%s]: ", prompt, def)
		} else {
			fmt.Printf("%s: ", prompt)
		}
		line, _ := reader.ReadString('\n')
		line = strings.TrimSpace(line)
		if line == "" {
			return def
		}
		return line
	}

	cfg := Config{
		Listen:  ask("listen", "0.0.0.0:443"),
		Domain:  ask("domain (empty = plain HTTP mode, no TLS)", ""),
		Stealth: StealthConfig{ServerName: ask("stealth server_name", "nginx/1.24.0")},
	}
	if cfg.Domain != "" {
		cfg.ACME.Email = ask("acme email", "")
		cfg.ACME.CacheDir = ask("acme cache_dir", "/var/lib/https_proxy/acme")
	}
	for {
		username := ask("username (empty to finish)", "")
		if username == "" {
			break
		}
		password := ask("password", "")
		if password == "" {
			fmt.Println("  (skipping user with empty password)")
			continue
		}
		cfg.Users = append(cfg.Users, User{Username: username, Password: password})
	}

	out, err := yaml.Marshal(&cfg)
	if err != nil {
		return err
	}
	if err := os.WriteFile("config.yaml", out, 0o600); err != nil {
		return err
	}
	fmt.Println("wrote config.yaml")
	return nil
}
