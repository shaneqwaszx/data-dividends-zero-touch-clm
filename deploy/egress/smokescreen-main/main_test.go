package main

import (
	"net/http"
	"net/url"
	"testing"
)

const testFQDN = "goldtier.r3-harness.invalid"
const testAuthority = testFQDN + ":443"

func head(lines ...string) []byte {
	s := ""
	for _, l := range lines {
		s += l + "\r\n"
	}
	return []byte(s + "\r\n")
}

func TestCheckHeadAcceptsOnlyTheExactConnect(t *testing.T) {
	ok := [][]byte{
		head("CONNECT "+testAuthority+" HTTP/1.1", "Host: "+testAuthority),
		head("CONNECT "+testAuthority+" HTTP/1.1", "Host: "+testAuthority, "Accept: */*", "User-Agent: x"),
		head("CONNECT "+testAuthority+" HTTP/1.1", "host:"+testAuthority, "Proxy-Connection: keep-alive"),
	}
	for _, h := range ok {
		if r := checkHead(h, testAuthority); r != "" {
			t.Fatalf("exact CONNECT refused (%s): %q", r, h)
		}
	}
}

func TestCheckHeadRefusesEveryVariant(t *testing.T) {
	host := "Host: " + testAuthority
	refused := map[string][]byte{
		"uppercase":         head("CONNECT GOLDTIER.R3-HARNESS.INVALID:443 HTTP/1.1", host),
		"mixed-case":        head("CONNECT GoldTier.r3-harness.invalid:443 HTTP/1.1", host),
		"trailing-dot":      head("CONNECT "+testFQDN+".:443 HTTP/1.1", host),
		"double-dot":        head("CONNECT "+testFQDN+"..:443 HTTP/1.1", host),
		"userinfo":          head("CONNECT user:pw@"+testAuthority+" HTTP/1.1", host),
		"fullwidth-dot":     head("CONNECT goldtier．r3-harness.invalid:443 HTTP/1.1", host),
		"pct-encoded":       head("CONNECT goldtier%2er3-harness.invalid:443 HTTP/1.1", host),
		"ip-literal":        head("CONNECT 34.120.0.10:443 HTTP/1.1", host),
		"ipv6-literal":      head("CONNECT [::1]:443 HTTP/1.1", host),
		"port-80":           head("CONNECT "+testFQDN+":80 HTTP/1.1", host),
		"port-0443":         head("CONNECT "+testFQDN+":0443 HTTP/1.1", host),
		"no-port":           head("CONNECT "+testFQDN+" HTTP/1.1", host),
		"subdomain":         head("CONNECT x."+testAuthority+" HTTP/1.1", host),
		"http10":            head("CONNECT "+testAuthority+" HTTP/1.0", host),
		"double-space":      head("CONNECT  "+testAuthority+" HTTP/1.1", host),
		"lowercase-method":  head("connect "+testAuthority+" HTTP/1.1", host),
		"absolute-get":      head("GET http://"+testFQDN+"/ HTTP/1.1", "Host: "+testFQDN),
		"absolute-get-443":  head("GET http://"+testAuthority+"/ HTTP/1.1", host),
		"origin-get":        head("GET / HTTP/1.1", host),
		"post":              head("POST http://"+testAuthority+"/ HTTP/1.1", host),
		"no-host":           head("CONNECT " + testAuthority + " HTTP/1.1"),
		"two-hosts":         head("CONNECT "+testAuthority+" HTTP/1.1", host, host),
		"conflicting-host":  head("CONNECT "+testAuthority+" HTTP/1.1", "Host: example.invalid:443"),
		"host-uppercase":    head("CONNECT "+testAuthority+" HTTP/1.1", "Host: GOLDTIER.R3-HARNESS.INVALID:443"),
		"host-no-port":      head("CONNECT "+testAuthority+" HTTP/1.1", "Host: "+testFQDN),
		"host-trailing-ows": head("CONNECT "+testAuthority+" HTTP/1.1", host+" "),
		"upstream-header":   head("CONNECT "+testAuthority+" HTTP/1.1", host, "X-Https-Upstream-Proxy: evil.invalid:443"),
		"proxy-auth":        head("CONNECT "+testAuthority+" HTTP/1.1", host, "Proxy-Authorization: Basic eA=="),
		"folded-header":     head("CONNECT "+testAuthority+" HTTP/1.1", host, " folded"),
		"tab":               head("CONNECT\t"+testAuthority+" HTTP/1.1", host),
		"bare-lf":           []byte("CONNECT " + testAuthority + " HTTP/1.1\nHost: " + testAuthority + "\r\n\r\n"),
		"nul":               head("CONNECT "+testAuthority+" HTTP/1.1", host+"\x00"),
		"incomplete":        []byte("CONNECT " + testAuthority + " HTTP/1.1\r\n"),
	}
	for name, h := range refused {
		if checkHead(h, testAuthority) == "" {
			t.Errorf("%s accepted: %q", name, h)
		}
	}
}

func TestExactConnectOnlyHook(t *testing.T) {
	hook := exactConnectOnly(testAuthority)
	good := &http.Request{Method: http.MethodConnect, RequestURI: testAuthority, Host: testAuthority, URL: &url.URL{Host: testAuthority}}
	if err := hook(good); err != nil {
		t.Fatalf("exact CONNECT refused: %v", err)
	}
	bad := []*http.Request{
		{Method: http.MethodGet, RequestURI: testAuthority, Host: testAuthority, URL: &url.URL{}},
		{Method: http.MethodConnect, RequestURI: "user@" + testAuthority, Host: testAuthority, URL: &url.URL{}},
		{Method: http.MethodConnect, RequestURI: testAuthority, Host: "GOLDTIER.R3-HARNESS.INVALID:443", URL: &url.URL{}},
		{Method: http.MethodConnect, RequestURI: testAuthority, Host: testAuthority, URL: &url.URL{User: url.User("u")}},
	}
	for i, r := range bad {
		if hook(r) == nil {
			t.Errorf("case %d accepted", i)
		}
	}
}

func TestValidFQDN(t *testing.T) {
	for _, s := range []string{testFQDN, "portal.gt.example.com"} {
		if !validFQDN(s) {
			t.Errorf("%s refused", s)
		}
	}
	for _, s := range []string{"", "localhost", "GOLDTIER.example.com", "a.example.com.", "34.120.0.10", "a..b.com", "-a.example.com", "a.b_c.com", "xn--.com", "a.123"} {
		if validFQDN(s) {
			t.Errorf("%s accepted", s)
		}
	}
}
