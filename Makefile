# 🦉 OWL-AGENT — development helpers
#   make help        list all targets
#   make setup       create venv + install Python deps
#   make test        run the pytest suite
#   make server      start the HTTP API server
SHELL := /bin/bash
VENV  := venv
PY    := $(VENV)/bin/python

# Locate the Go toolchain even when it is not on the default PATH (e.g. /usr/local/go/bin).
GO := $(shell command -v go 2>/dev/null || echo /usr/local/go/bin/go)

.PHONY: help setup install wheel test server stats fetch build-proxies go-build go-test prox5 lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

setup: ## Create the venv and install Python dependencies
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

install: ## Install owl-agent into the venv as an editable Python module
	$(VENV)/bin/pip install -e .

wheel: ## Build a distributable wheel into dist/
	$(VENV)/bin/pip wheel . --no-deps -w dist

test: ## Run the pytest suite
	$(PY) -m pytest tests/ -v --tb=short

server: ## Start the HTTP API server (binds 0.0.0.0, honors PORT)
	bash run.sh server --host 0.0.0.0 --api-port $${PORT:-60000}

stats: ## Show proxy pool stats
	bash run.sh status

fetch: ## Fetch a URL: make fetch URL=https://example.com
	bash run.sh fetch $(URL)

build-proxies: ## Build all proxy integrations (needs Go 1.22+ and Rust 1.70+)
	bash proxies/build.sh

go-build: ## Build the Go proxy binaries (prox5 wrapper + https_proxy_go)
	PATH="$(dir $(GO)):$$PATH" bash proxies/prox5/build.sh
	PATH="$(dir $(GO)):$$PATH" bash proxies/https_proxy_go/build.sh

go-test: ## Run Go tests for the https_proxy Go port
	cd proxies/https_proxy_go && $(GO) test ./...

prox5: ## Run the local prox5 SOCKS5 server (build it first)
	bash run.sh prox5

lint: ## Ruff lint (Python)
	ruff check . --select E,F,W --ignore E501,E741,F841

clean: ## Remove the venv and proxy build artifacts
	rm -rf $(VENV) proxies/bin
