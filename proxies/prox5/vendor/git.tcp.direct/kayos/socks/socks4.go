package socks

import (
	"net"
	"time"
)

func (sesh *session) dialSocks4(targetAddr string) (_ net.Conn, err error) {
	socksType := sesh.Proto

	conn, err := sesh.internalDial()
	if err != nil {
		return nil, err
	}

	// connection request
	host, port, err := splitHostPort(targetAddr)
	if err != nil {
		return nil, err
	}
	ip := net.IPv4(0, 0, 0, 1).To4()
	if socksType == SOCKS4 {
		ip, err = lookupIPv4(host)
		if err != nil {
			return nil, err
		}
	}
	req := newRequestBuilder()
	req.MustWriteByte(4)               // socks version 4
	req.MustWriteByte(1)               // command 1 (CONNECT)
	req.MustWriteByte(byte(port >> 8)) // higher byte of destination port
	req.MustWriteByte(byte(port))      // lower byte of destination port (big endian)

	// target IP address
	req.MustWriteByte(ip[0])
	req.MustWriteByte(ip[1])
	req.MustWriteByte(ip[2])
	req.MustWriteByte(ip[3])

	req.MustWriteByte(0) // user id is empty, anonymous proxy only

	if socksType == SOCKS4A {
		_, _ = req.WriteString(host)
		req.MustWriteByte(0)
	}

	resp, err := sesh.sendReceive(conn, req.Bytes())

	defer func() {
		bufs.MustPut(req.Buffer)
		req.Buffer = nil
	}()

	switch {
	case err != nil:
		return nil, err
	case len(resp) != 8:
		return nil, ErrImproperProtocolResponse
	case resp[1] == 90:
		//
	case resp[1] == 91:
		return nil, ErrRejectedOrFailed
	case resp[1] == 92:
		return nil, ErrIdentdFailed
	case resp[1] == 93:
		return nil, ErrIdentMismatch
	default:
		return nil, ErrUnknownFailure
	}

	// clear the deadline before returning
	err = conn.SetDeadline(time.Time{})

	return conn, err
}
