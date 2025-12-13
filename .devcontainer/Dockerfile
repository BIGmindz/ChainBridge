# ChainBridge Dev Container - Custom Dockerfile
# Extends base Python dev container with project-specific tooling

FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    jq \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install global Python tools
RUN pip install --no-cache-dir \
    pytest \
    pytest-xdist \
    pytest-benchmark \
    pre-commit \
    ruff \
    black \
    isort \
    httpie

# Set up non-root user environment
USER vscode
WORKDIR /workspaces/ChainBridge

# Default shell customization
RUN echo 'alias ll="ls -la"' >> ~/.bashrc \
    && echo 'alias pytest="python -m pytest"' >> ~/.bashrc \
    && echo 'alias ultra="make ultra"' >> ~/.bashrc \
    && echo 'alias turbo="make turbo"' >> ~/.bashrc

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s CMD python --version || exit 1
