# syntax=docker/dockerfile:1.7
# R3 GoldTier egress image (D-127). One image, two roles chosen by CLM_EGRESS_ROLE:
#   proxy    - Smokescreen (pinned commit) under the guard
#   resolver - CoreDNS (pinned release, checksum-verified) under the guard
# Every source is pinned by digest, commit or checksum. Build context: deploy/egress.
# See deploy/egress/SMOKESCREEN_PIN.md for the pin and update policy.

ARG GO_IMAGE=golang:1.26-bookworm@sha256:dc40a13b61304647ed7e5d581d246b86413dfc29d63c6d018310feb93cd98fc0
ARG RUNTIME_IMAGE=python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

# --- Smokescreen, built from a pinned commit with its vendored, go.sum-checked modules -----
FROM ${GO_IMAGE} AS smokescreen
ADD --keep-git-dir=false https://github.com/stripe/smokescreen.git#bb9ed1bbe75b59821f881dd0c1411c79dd7abdbe /src
# The R3 entrypoint (smokescreen-main/main.go) is compiled inside the pinned module so that it
# links only the pinned, vendored code. Upstream's own main is built too, for comparison only.
COPY smokescreen-main/main.go smokescreen-main/main_test.go /src/r3egress/
WORKDIR /src
RUN CGO_ENABLED=0 GOFLAGS=-mod=vendor go test -count=1 ./r3egress \
 && CGO_ENABLED=0 GOFLAGS=-mod=vendor go build -trimpath -ldflags="-s -w -buildid=" -o /out/smokescreen ./r3egress \
 && CGO_ENABLED=0 GOFLAGS=-mod=vendor go build -trimpath -ldflags="-s -w -buildid=" -o /out/smokescreen-upstream . \
 && /out/smokescreen --help >/dev/null

# --- CoreDNS release binary, verified by its published SHA-256 -----------------------------
FROM ${RUNTIME_IMAGE} AS coredns
ADD --checksum=sha256:2495c5b8f3fab6d0a336c397f1227b75406d86e6ec7125744a29df9e936ab8cd \
    https://github.com/coredns/coredns/releases/download/v1.15.0/coredns_1.15.0_linux_amd64.tgz /tmp/coredns.tgz
RUN mkdir /out && tar -xzf /tmp/coredns.tgz -C /out coredns && /out/coredns -version

# --- Runtime base: binaries plus nft and setpriv, no guard (used for the S2 gate runs) ------
FROM ${RUNTIME_IMAGE} AS runtime-base
RUN apt-get update \
 && apt-get install -y --no-install-recommends nftables=1.0.6-2+deb12u2 \
 && rm -rf /var/lib/apt/lists/* \
 && command -v setpriv nft
COPY --from=smokescreen /out/smokescreen /usr/local/bin/smokescreen
COPY --from=coredns /out/coredns /usr/local/bin/coredns
RUN chmod 0555 /usr/local/bin/smokescreen /usr/local/bin/coredns

# --- Gate-comparison image only: adds upstream's unmodified main -------------------------
FROM runtime-base AS gate-compare
COPY --from=smokescreen /out/smokescreen-upstream /usr/local/bin/smokescreen-upstream

# --- Final image -------------------------------------------------------------------------
FROM runtime-base AS runtime
# The guard runs as root WITHOUT CAP_DAC_OVERRIDE, so the directory needs its own r-x bits.
RUN install -d -o root -g root -m 0555 /opt/egress
COPY --chmod=0444 goldtier_egress_guard.py Corefile.template /opt/egress/
ENV PYTHONDONTWRITEBYTECODE=1
STOPSIGNAL SIGTERM
ENTRYPOINT ["/usr/local/bin/python3", "-I", "/opt/egress/goldtier_egress_guard.py"]
