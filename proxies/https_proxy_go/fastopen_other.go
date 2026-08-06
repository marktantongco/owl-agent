//go:build !linux && !darwin

package main

import "net"

// fastOpenListener is a no-op on platforms without TCP Fast Open support
// (Windows, etc.) — a plain listener is used instead.
func fastOpenListener(addr string) (net.Listener, error) {
	return net.Listen("tcp", addr)
}
