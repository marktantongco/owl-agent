//go:build linux || darwin

package main

import (
	"context"
	"net"
	"syscall"

	"golang.org/x/sys/unix"
)

// fastOpenListener returns a TCP listener with TCP Fast Open (TFO) enabled.
// Only built on platforms where x/sys/unix exposes TCP_FASTOPEN.
func fastOpenListener(addr string) (net.Listener, error) {
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
	return lc.Listen(context.Background(), "tcp", addr)
}
