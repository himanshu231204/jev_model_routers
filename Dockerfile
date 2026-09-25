# JEV Router, packaged with the CLIs it wraps (Claude Code, OpenAI Codex).
#
# This image is for people who want jev-claude / jev-codex without a local Python or Node
# setup. It does not need Docker for normal development — `pip install jev-model-router` is
# the default install path; see docs/quickstart.md. Build/publish is covered in RELEASE.md.
FROM node:20-slim AS base

# Claude Code and Codex are Node CLIs; JEV Router itself is pure-stdlib Python with no
# runtime dependencies (see pyproject.toml).
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code @openai/codex \
    && npm cache clean --force

# Build the wheel from this checkout rather than pulling from PyPI, so the image always
# matches the source it was built from (including on a pre-release commit).
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --break-system-packages --no-cache-dir .

# Run as a non-root user; Claude Code and Codex both expect a writable $HOME for their own
# config/auth (~/.claude, ~/.codex), which the run command must mount or set up.
RUN useradd --create-home --shell /bin/bash jev
USER jev
WORKDIR /work
ENV HOME=/home/jev

ENTRYPOINT ["jev-claude"]
