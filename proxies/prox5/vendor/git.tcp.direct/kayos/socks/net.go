package socks

import (
	"fmt"
	"net"
	"strconv"
	"sync"
	"time"

	"git.tcp.direct/kayos/common/pool"
)

var bufs = pool.NewBufferFactory()

func newRequestBuilder() *requestBuilder {
	return &requestBuilder{bufs.Get()}
}

type requestBuilder struct {
	*pool.Buffer
}

func (sesh *session) sendReceive(conn net.Conn, req []byte) (resp []byte, err error) {
	// fmt.Printf("sendReceive: %v->%v\n", conn.LocalAddr(), conn.RemoteAddr())
	// spew.Dump(req)
	if sesh.Timeout > 0 {
		if err = conn.SetWriteDeadline(time.Now().Add(sesh.Timeout)); err != nil {
			return nil, err
		}
	}
	// fmt.Printf("sendReceive write: %v->%v\n", conn.LocalAddr(), conn.RemoteAddr())
	// var n int
	// n, err = conn.Write(req)
	_, err = conn.Write(req)
	if err != nil {
		return
	}
	// fmt.Printf("sendReceive write: %v->%v, %d bytes\n", conn.LocalAddr(), conn.RemoteAddr(), n)

	// fmt.Printf("sendReceive read: %v->%v\n", conn.LocalAddr(), conn.RemoteAddr())
	resp, err = sesh.readAll(conn)
	return
}

var bufPool = &sync.Pool{
	New: func() any { return make([]byte, 1024) },
}

func (sesh *session) readAll(conn net.Conn) ([]byte, error) {
	resp := bufPool.Get().([]byte)
	defer bufPool.Put(resp)

	if sesh.Timeout > 0 {
		if err := conn.SetReadDeadline(time.Now().Add(sesh.Timeout)); err != nil {
			return nil, err
		}
	}

	n, err := conn.Read(resp)
	return resp[:n], err
}

func lookupIPv4(host string) (net.IP, error) {
	ips, err := net.LookupIP(host)
	if err != nil {
		return nil, err
	}
	for _, ip := range ips {
		ipv4 := ip.To4()
		if ipv4 == nil {
			continue
		}
		return ipv4, nil
	}
	return nil, fmt.Errorf("no IPv4 address found for host: %s", host)
}

func splitHostPort(addr string) (host string, port uint16, err error) {
	host, portStr, err := net.SplitHostPort(addr)
	if err != nil {
		return "", 0, err
	}
	portInt, err := strconv.ParseUint(portStr, 10, 16)
	if err != nil {
		return "", 0, err
	}
	port = uint16(portInt)
	return
}
