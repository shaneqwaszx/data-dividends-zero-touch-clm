# syntax=docker/dockerfile:1.7
# Hosted GPT-OSS egress image (D-138 A1, PROPOSED; LOCAL DESIGN CANDIDATE, not approved for AWS).
# One image, two roles chosen by CLM_EGRESS_ROLE (proxy: Smokescreen; resolver: CoreDNS), both
# under openrouter_egress_guard.py. It reuses R3's reviewed build (deploy/egress/Dockerfile,
# D-127) unchanged: the same pinned Smokescreen commit, CoreDNS checksum, Go builder and runtime
# digests (tests/test_openrouter_egress.py asserts they are equal), and R3's own entrypoint
# (smokescreen-main/main.go, its tests run in the build) and Corefile.template, taken from the
# named build context "r3". Only the guard differs. Build (from the repository root):
#   docker buildx build --build-context r3=deploy/egress \
#     -f apps/assistant/deploy/egress/openrouter-egress.Dockerfile apps/assistant/deploy/egress

ARG GO_IMAGE=golang:1.26-bookworm@sha256:dc40a13b61304647ed7e5d581d246b86413dfc29d63c6d018310feb93cd98fc0
ARG RUNTIME_IMAGE=python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

FROM ${GO_IMAGE} AS smokescreen
ADD --keep-git-dir=false https://github.com/stripe/smokescreen.git#bb9ed1bbe75b59821f881dd0c1411c79dd7abdbe /src
COPY --from=r3 smokescreen-main/main.go smokescreen-main/main_test.go /src/r3egress/
WORKDIR /src
RUN CGO_ENABLED=0 GOFLAGS=-mod=vendor go test -count=1 ./r3egress \
 && CGO_ENABLED=0 GOFLAGS=-mod=vendor go build -trimpath -ldflags="-s -w -buildid=" -o /out/smokescreen ./r3egress \
 && /out/smokescreen --help >/dev/null

FROM ${RUNTIME_IMAGE} AS coredns
ADD --checksum=sha256:2495c5b8f3fab6d0a336c397f1227b75406d86e6ec7125744a29df9e936ab8cd \
    https://github.com/coredns/coredns/releases/download/v1.15.0/coredns_1.15.0_linux_amd64.tgz /tmp/coredns.tgz
RUN mkdir /out && tar -xzf /tmp/coredns.tgz -C /out coredns && /out/coredns -version

FROM ${RUNTIME_IMAGE} AS runtime
RUN apt-get update \
 && apt-get install -y --no-install-recommends nftables=1.0.6-2+deb12u2 \
 && rm -rf /var/lib/apt/lists/* \
 && command -v setpriv nft
COPY --from=smokescreen /out/smokescreen /usr/local/bin/smokescreen
COPY --from=coredns /out/coredns /usr/local/bin/coredns
RUN chmod 0555 /usr/local/bin/smokescreen /usr/local/bin/coredns \
 && install -d -o root -g root -m 0555 /opt/egress
COPY --chmod=0444 openrouter_egress_guard.py /opt/egress/
COPY --chmod=0444 --from=r3 Corefile.template /opt/egress/
ENV PYTHONDONTWRITEBYTECODE=1
STOPSIGNAL SIGTERM
ENTRYPOINT ["/usr/local/bin/python3", "-I", "/opt/egress/openrouter_egress_guard.py"]
