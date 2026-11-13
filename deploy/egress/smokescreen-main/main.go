// R3 GoldTier egress entrypoint for Smokescreen (D-127).
//
// Built inside the pinned Smokescreen module (see ../SMOKESCREEN_PIN.md), so it links the
// pinned, vendored library code unchanged. Upstream's own main derives the role from a TLS
// client certificate; the README documents replacing RoleFromRequest for other deployments.
// This entrypoint can only narrow what Smokescreen accepts. It never widens it:
//
//  1. RoleFromRequest returns one fixed role. There is no authentication in either build; the
//     only client is the backend on the internal goldtier-control network. The ACL file gives
//     that role exactly one domain, and its default rule (any other role) allows nothing.
//  2. A raw request-head gate (owner decision G2-P2, option B) runs on every accepted
//     connection BEFORE Go's HTTP parser, Smokescreen's ACL, IDNA mapping or DNS. The first
//     request on a connection must be exactly
//         CONNECT <fqdn>:443 HTTP/1.1
//     with exactly one "Host: <fqdn>:443" header, only printable ASCII, and only allowlisted
//     header names. Anything else is answered 403 and closed without any lookup.
//  3. PostDecisionRequestHandler re-checks the parsed request after Smokescreen has itself
//     allowed it (method CONNECT, RequestURI and Host byte-equal to <fqdn>:443, no userinfo).
//
// Smokescreen's ACL, private-range denial and --deny-range set stay in force independently.
package main

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/stripe/smokescreen/cmd"
	"github.com/stripe/smokescreen/pkg/smokescreen"
)

const (
	backendRole  = "goldtier-backend"
	fqdnEnv      = "R3_EGRESS_FQDN"
	maxHeadBytes = 4096
	headTimeout  = 5 * time.Second
)

var (
	fqdnPattern    = regexp.MustCompile(`^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,61}[a-z0-9]$`)
	allowedHeaders = map[string]bool{
		"host": true, "accept": true, "user-agent": true, "proxy-connection": true, "connection": true,
	}
	errHead = errors.New("r3: request head refused")
)

// validFQDN accepts only a lowercase ASCII LDH name with at least two labels.
func validFQDN(s string) bool {
	return len(s) <= 253 && fqdnPattern.MatchString(s) && net.ParseIP(s) == nil
}

// checkHead validates one complete request head (bytes up to and including CRLFCRLF).
// It returns a short reason code on refusal; it never echoes request content.
func checkHead(head []byte, authority string) string {
	for _, b := range head {
		if b != '\r' && b != '\n' && (b < 0x20 || b > 0x7e) {
			return "non_ascii_or_control_byte"
		}
	}
	if !bytes.HasSuffix(head, []byte("\r\n\r\n")) {
		return "incomplete_head"
	}
	lines := strings.Split(string(head[:len(head)-4]), "\r\n")
	if lines[0] != "CONNECT "+authority+" HTTP/1.1" {
		return "request_line_not_exact_connect"
	}
	hosts := 0
	for _, line := range lines[1:] {
		name, value, ok := strings.Cut(line, ":")
		if !ok || name == "" || strings.ContainsAny(name, " \t") || strings.ContainsAny(line, "\r\n") {
			return "malformed_header"
		}
		lname := strings.ToLower(name)
		if !allowedHeaders[lname] {
			return "header_not_allowed"
		}
		if lname == "host" {
			hosts++
			if strings.TrimLeft(value, " ") != authority {
				return "host_header_not_exact"
			}
		}
	}
	if hosts != 1 {
		return "host_header_count"
	}
	return ""
}

// gatedConn reads and validates the first request head before handing any byte to the
// HTTP server. A refused connection gets a fixed 403 and is closed.
type gatedConn struct {
	net.Conn
	authority string
	logger    *logrus.Logger
	once      sync.Once
	pending   []byte
	err       error
}

func (c *gatedConn) gate() {
	_ = c.Conn.SetReadDeadline(time.Now().Add(headTimeout))
	buf := make([]byte, 0, maxHeadBytes)
	chunk := make([]byte, 512)
	for !bytes.Contains(buf, []byte("\r\n\r\n")) {
		if len(buf) >= maxHeadBytes {
			c.refuse("head_too_large")
			return
		}
		n, err := c.Conn.Read(chunk[:min(len(chunk), maxHeadBytes-len(buf))])
		buf = append(buf, chunk[:n]...)
		if err != nil {
			c.refuse("head_read_error")
			return
		}
	}
	_ = c.Conn.SetReadDeadline(time.Time{})
	end := bytes.Index(buf, []byte("\r\n\r\n")) + 4
	if reason := checkHead(buf[:end], c.authority); reason != "" {
		c.refuse(reason)
		return
	}
	c.pending = buf
}

func (c *gatedConn) refuse(reason string) {
	c.logger.WithFields(logrus.Fields{
		"r3_gate": "refused", "reason": reason, "inbound_remote_addr": c.Conn.RemoteAddr().String(),
	}).Warn("R3-REQUEST-HEAD-GATE")
	_, _ = c.Conn.Write([]byte("HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"))
	_ = c.Conn.Close()
	c.err = errHead
}

func (c *gatedConn) Read(p []byte) (int, error) {
	c.once.Do(c.gate)
	if c.err != nil {
		return 0, io.EOF
	}
	if len(c.pending) > 0 {
		n := copy(p, c.pending)
		c.pending = c.pending[n:]
		return n, nil
	}
	return c.Conn.Read(p)
}

type gatedListener struct {
	net.Listener
	authority string
	logger    *logrus.Logger
}

func (l gatedListener) Accept() (net.Conn, error) {
	conn, err := l.Listener.Accept()
	if err != nil {
		return nil, err
	}
	return &gatedConn{Conn: conn, authority: l.authority, logger: l.logger}, nil
}

func exactConnectOnly(authority string) func(*http.Request) error {
	return func(req *http.Request) error {
		if req.Method != http.MethodConnect || req.RequestURI != authority || req.Host != authority ||
			(req.URL != nil && req.URL.User != nil) {
			return errors.New("r3: only CONNECT " + authority + " is permitted")
		}
		return nil
	}
}

func main() {
	conf, err := cmd.NewConfiguration(nil, nil)
	if err != nil {
		logrus.Fatalf("Could not create configuration: %v", err)
	}
	if conf == nil {
		return // --help or --version was handled by NewConfiguration
	}
	fqdn := os.Getenv(fqdnEnv)
	if !validFQDN(fqdn) {
		logrus.Fatalf("r3: %s must be a lowercase ASCII FQDN", fqdnEnv)
	}
	authority := fqdn + ":443"
	conf.Log.Formatter = &logrus.JSONFormatter{}
	conf.RoleFromRequest = func(*http.Request) (string, error) { return backendRole, nil }
	conf.PostDecisionRequestHandler = exactConnectOnly(authority)
	inner, err := net.Listen("tcp", fmt.Sprintf("%s:%d", conf.Ip, conf.Port))
	if err != nil {
		logrus.Fatalf("r3: listen: %v", err)
	}
	conf.Listener = gatedListener{Listener: inner, authority: authority, logger: conf.Log}
	log.SetOutput(&smokescreen.Log2LogrusWriter{Entry: conf.Log.WithField("stdlog", "1")})
	log.SetFlags(0)
	smokescreen.StartWithConfig(conf, nil)
}
