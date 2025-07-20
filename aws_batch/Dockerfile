# Multi-stage build for optimal image size
FROM golang:1.18-alpine AS builder

# Install CA certificates
RUN apk add --no-cache ca-certificates

# Set working directory
WORKDIR /build

# Copy go mod files first for better caching
COPY src/go.mod src/go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY src/index.go ./

# Build the binary with optimizations
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s" \
    -o ocr-processor \
    index.go

# Final stage - minimal runtime image
FROM scratch

# Copy CA certificates for HTTPS
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy the binary
COPY --from=builder /build/ocr-processor /ocr-processor

# Set non-root user (scratch doesn't have users, but we can use UID)
USER 1001

# Run the binary
ENTRYPOINT ["/ocr-processor"]