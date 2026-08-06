package socks

import "errors"

var (
	ErrImproperProtocolResponse = errors.New("SOCKS server does not respond properly")
	ErrRejectedOrFailed         = errors.New("socks connection request rejected or failed")
	ErrIdentdFailed             = errors.New("socks connection request rejected because SOCKS server cannot connect to identd on the client")
	ErrIdentMismatch            = errors.New("socks connection request rejected because the client program and identd report different user-ids")
	ErrUnknownFailure           = errors.New("socks connection request failed, unknown error")
)
