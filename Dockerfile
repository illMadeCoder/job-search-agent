# Job Search Agent Container
# Runs as non-root user with minimal permissions

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Go (for beads)
RUN curl -fsSL https://go.dev/dl/go1.22.0.linux-amd64.tar.gz | tar -C /usr/local -xzf -
ENV PATH="/usr/local/go/bin:/home/agent/go/bin:${PATH}"
ENV GOPATH="/home/agent/go"

# Install Claude CLI
RUN curl -fsSL https://cli.anthropic.com/install.sh | sh
ENV PATH="/root/.claude/bin:${PATH}"

# Create non-root user
RUN useradd -m -s /bin/bash agent
USER agent
WORKDIR /home/agent/job-search

# Install beads as agent user
RUN go install github.com/steveyegge/beads/cmd/bd@latest

# Copy requirements and install Python deps
COPY --chown=agent:agent requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Environment
ENV PATH="/home/agent/.local/bin:/home/agent/go/bin:${PATH}"

# Entry point - run the daily agent
COPY --chown=agent:agent docker-entrypoint.sh /home/agent/
RUN chmod +x /home/agent/docker-entrypoint.sh

ENTRYPOINT ["/home/agent/docker-entrypoint.sh"]
CMD ["daily"]
