# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OCC-P66-DOCKER: SOVEREIGN CONTAINERIZATION
# ═══════════════════════════════════════════════════════════════════════════════
# CONSTITUTIONAL INVARIANTS:
#   - Control > Autonomy: NO SHELL. Attackers cannot exec if there's no shell.
#   - Proof > Execution: Built in Clean Room (Stage 1), shipped from Vault (Stage 2).
#   - Zero Drift: Image tag locks environment. v0.1.0-ALPHA is immutable.
# ═══════════════════════════════════════════════════════════════════════════════

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ STAGE 1: THE FORGE (Builder)                                                │
# │ Purpose: Compile the Rust binary in a clean, reproducible environment.      │
# │ This stage contains the full Rust toolchain (~1.2GB) but is DISCARDED.      │
# └─────────────────────────────────────────────────────────────────────────────┘
FROM rust:1.83-slim-bookworm AS builder

# Install build dependencies for crypto libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/chainbridge

# Copy manifests first for layer caching
COPY Cargo.toml Cargo.lock ./

# Create dummy src to cache dependencies
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# Copy actual source code
COPY src ./src
COPY benches ./benches

# Build for Release (Optimized) - Touch main.rs to force rebuild
RUN touch src/main.rs && cargo build --release

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ STAGE 2: THE VAULT (Runtime)                                                │
# │ Purpose: Minimal runtime with ZERO attack surface.                          │
# │ Base: gcr.io/distroless/cc-debian12                                         │
# │   - No shell (/bin/bash does not exist)                                     │
# │   - No package manager (apt-get does not exist)                             │
# │   - No utilities (ls, cat, curl do not exist)                               │
# │   - Contains: glibc, libgcc, openssl (required by Rust binaries)            │
# └─────────────────────────────────────────────────────────────────────────────┘
FROM gcr.io/distroless/cc-debian12

# Copy ONLY the compiled binary from the builder stage
# Everything else (source code, Cargo, rustc) is left behind
COPY --from=builder /usr/src/chainbridge/target/release/chainbridge_kernel /usr/local/bin/chainbridge_kernel

# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY: Run as non-root user to minimize attack surface
# distroless/cc includes 'nonroot' user (UID 65532)
# ═══════════════════════════════════════════════════════════════════════════════
USER nonroot:nonroot

# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT: Port 8080 is the ONLY door into this container.
# All traffic flows through the GaaS Gateway HTTP endpoint.
# ═══════════════════════════════════════════════════════════════════════════════
EXPOSE 8080

# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT: Fail-Closed Entrypoint
# The container does ONE thing: run the kernel. Nothing else.
# If the kernel crashes, the container dies. No zombie processes.
# ═══════════════════════════════════════════════════════════════════════════════
CMD ["chainbridge_kernel"]
