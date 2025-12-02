# Colima E2B - Default Template
# Lightweight Ubuntu base with essential tools

FROM ubuntu:22.04

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install essential tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    git \
    vim \
    nano \
    inotify-tools \
    procps \
    htop \
    jq \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd -m -s /bin/bash -u 1000 user \
    && mkdir -p /home/user/workspace \
    && chown -R user:user /home/user

# Create directory for PID tracking
RUN mkdir -p /tmp/pids && chmod 777 /tmp/pids

# Add run-tracked script for process tracking
RUN echo '#!/bin/bash\necho "$$" > /tmp/pids/$1\nexec "${@:2}"' > /usr/local/bin/run-tracked \
    && chmod +x /usr/local/bin/run-tracked

# Switch to user
USER user
WORKDIR /home/user/workspace

# Environment
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH
ENV TERM=xterm-256color

# Keep container running
CMD ["sleep", "infinity"]
