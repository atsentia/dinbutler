FROM ubuntu:22.04

# Set non-interactive frontend
ENV DEBIAN_FRONTEND=noninteractive

# Install base packages
RUN apt-get update && apt-get install -y \
    curl \
    git \
    sudo \
    zsh \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -s /bin/zsh -u 1001 coder
RUN echo "coder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Install bash
RUN apt-get update && apt-get install -y bash

# Switch to the non-root user
USER coder
WORKDIR /home/coder

# Install and setup Gemini CLI
RUN curl -o /tmp/gemini-cli.zip https://storage.googleapis.com/cloud-sdk-release/google-cloud-sdk-470.0.0-linux-x86_64.tar.gz && \
    tar -xf /tmp/gemini-cli.zip -C /home/coder && \
    mv /home/coder/google-cloud-sdk /home/coder/.gemini-cli && \
    bash /home/coder/.gemini-cli/install.sh -q && \
    echo 'export PATH="/home/coder/.gemini-cli/bin:$PATH"' >> /home/coder/.zshrc

# Set the entrypoint
CMD ["/bin/zsh"]