FROM node:22-bookworm-slim

ARG OPENCODE_VERSION=1.18.13

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        binutils \
        build-essential \
        ca-certificates \
        coreutils \
        curl \
        file \
        gdb \
        git \
        jq \
        less \
        procps \
        python3 \
        python3-pip \
        ripgrep \
    && npm install --global "opencode-ai@${OPENCODE_VERSION}" \
    && npm cache clean --force \
    && rm -rf /var/lib/apt/lists/*

# Benchmark runs must be reproducible and must never publish their sessions.
ENV OPENCODE_DISABLE_AUTOUPDATE=true \
    OPENCODE_AUTO_SHARE=false

WORKDIR /workspace
