# FibCalc reproducible build image.
#
# Two-stage build:
#  1. builder — CGO-disabled static build of the default binary (no `gmp`
#     build tag). Profile-guided optimisation consumes
#     cmd/fibcalc/default.pgo when present.
#  2. runtime — distroless minimal base shipping only the linked binary.
#
# Build responsibility is delegated to the Makefile (audit STR-02): the compile
# flags — -trimpath, the PGO profile, and the three -X version symbols — live in
# exactly one place. This image used to repeat a bare `go build -ldflags="-s -w"`
# that omitted the version symbols entirely, so `docker run ... --version`
# reported "fibcalc dev / Commit: unknown / Built: unknown".
#
# .dockerignore excludes .git, so `git describe` cannot run inside the build.
# Pass the identity in explicitly; the defaults below are honest placeholders,
# not guesses at a version:
#
#   docker build \
#     --build-arg VERSION="$(git describe --tags --always --dirty)" \
#     --build-arg COMMIT="$(git rev-parse --short HEAD)" \
#     --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
#     -t fibcalc:local .

ARG GO_VERSION=1.26

# TODO(SEC-04): pin by digest — golang:${GO_VERSION}-bookworm@sha256:<...>
# Still open after the 2026-09-07 audit, for the same reason and no other: every
# environment this repository has been edited from lacks both a docker CLI and
# outbound registry access, so no digest can be resolved. A guessed digest is
# worse than a tag, so none is written here. Resolve on any machine with
# registry access and paste the result:
#     docker buildx imagetools inspect golang:1.26-bookworm --format '{{.Manifest.Digest}}'
#     crane digest golang:1.26-bookworm
FROM golang:${GO_VERSION}-bookworm AS builder

ENV CGO_ENABLED=0 \
    GOFLAGS=-trimpath

WORKDIR /src

# The Makefile is the build contract; golang:*-bookworm ships git but not make.
RUN apt-get update \
    && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

# Cache module downloads independently of source edits.
COPY go.mod go.sum ./
RUN go mod download

COPY . .

# Identity of the build, supplied by the caller (see header). The Makefile reads
# these as overridable variables and injects them via -X.
ARG VERSION=docker
ARG COMMIT=unknown
ARG BUILD_DATE=unknown

# `make build` applies -trimpath, the -X version symbols and the PGO profile
# from cmd/fibcalc/default.pgo when it is present. The --version call is a smoke
# test: it fails the build if the binary cannot start.
RUN make build VERSION="${VERSION}" COMMIT="${COMMIT}" BUILD_DATE="${BUILD_DATE}" \
    && mkdir -p /out \
    && cp build/fibcalc /out/fibcalc \
    && /out/fibcalc --version


# TODO(SEC-04): pin by digest — gcr.io/distroless/base-debian12@sha256:<...>
# Same reason as the builder stage above. Resolve with:
#     crane digest gcr.io/distroless/base-debian12
FROM gcr.io/distroless/base-debian12 AS runtime

COPY --from=builder /out/fibcalc /usr/local/bin/fibcalc

USER nonroot:nonroot
ENTRYPOINT ["/usr/local/bin/fibcalc"]
CMD ["--help"]
