FROM node:22-bookworm-slim

ARG CLAUDE_CODE_VERSION=latest

# The base image defaults to the unprivileged node user. Build-time package
# installation must run as root; the final image switches back to node.
USER root

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
    && npm install --global "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && npm cache clean --force \
    && rm -rf /var/lib/apt/lists/* \
    && claude --version

RUN mkdir -p /home/node/.claude \
    && chown -R node:node /home/node

ENV HOME=/home/node \
    DISABLE_AUTOUPDATER=1 \
    DISABLE_TELEMETRY=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

USER node
WORKDIR /workspace
