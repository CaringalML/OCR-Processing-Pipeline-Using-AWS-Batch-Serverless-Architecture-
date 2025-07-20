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

# Final stage - use alpine for AWS Batch compatibility
FROM alpine:3.18

# Install CA certificates and create user
RUN apk add --no-cache ca-certificates tzdata && \
    addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Copy the binary
COPY --from=builder /build/ocr-processor /usr/local/bin/ocr-processor

# Set permissions
RUN chmod +x /usr/local/bin/ocr-processor

# Switch to non-root user
USER appuser

# Run the binary
ENTRYPOINT ["/usr/local/bin/ocr-processor"]