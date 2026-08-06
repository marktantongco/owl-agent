package socks

import (
	"errors"
	"fmt"
	"net"
	"net/url"
	"time"
)

type (
	session struct {
		Proto   int
		Host    string
		Auth    *auth
		Timeout time.Duration
		conn    net.Conn
	}
	auth struct {
		Username string
		Password string
	}
)

func parse(proxyURI string) (*session, error) {
	uri, err := url.Parse(proxyURI)
	if err != nil {
		return nil, err
	}
	sesh := &session{}
	switch uri.Scheme {
	case "socks4":
		sesh.Proto = SOCKS4
	case "socks4a":
		sesh.Proto = SOCKS4A
	case "socks5":
		sesh.Proto = SOCKS5
	default:
		return nil, fmt.Errorf("unknown SOCKS protocol %s", uri.Scheme)
	}
	sesh.Host = uri.Host
	user := uri.User.Username()
	password, _ := uri.User.Password()
	if user != "" || password != "" {
		if user == "" || password == "" || len(user) > 255 || len(password) > 255 {
			return nil, errors.New("invalid user name or password")
		}
		sesh.Auth = &auth{
			Username: user,
			Password: password,
		}
	}
	query := uri.Query()
	timeout := query.Get("timeout")
	if timeout != "" {
		var err error
		sesh.Timeout, err = time.ParseDuration(timeout)
		if err != nil {
			return nil, err
		}
	}
	return sesh, nil
}
