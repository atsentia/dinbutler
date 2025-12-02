# Colima E2B - Node.js Template
# Node.js 20 LTS with common packages

FROM node:20-slim

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
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
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user (node image has user node, but we create 'user' for consistency)
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
WORKDIR /home/user

# Install global npm packages as user
RUN npm config set prefix '/home/user/.npm-global' \
    && npm install -g \
    typescript \
    ts-node \
    eslint \
    prettier \
    nodemon

# Set working directory
WORKDIR /home/user/workspace

# Environment
ENV HOME=/home/user
ENV PATH=/home/user/.npm-global/bin:/home/user/.local/bin:$PATH
ENV NODE_ENV=development
ENV TERM=xterm-256color

# Keep container running
CMD ["sleep", "infinity"]
