# Luqi-AI Multi-Track Laboratory Environment
# Build:  docker build -t luqi-lab-base lab/   (from repo root)
# This is the template image the LabSandboxManager spins up per student session.
FROM python:3.11-slim

# Non-root student user - the sandbox executes all student commands as this identity
RUN groupadd -r luqistudent && useradd -r -g luqistudent luqistudent

# Core diagnostic + networking utilities for the practical tracks
RUN apt-get update && apt-get install -y --no-install-recommends     net-tools     iputils-ping     curl     git     && rm -rf /var/lib/apt/lists/*

WORKDIR /home/luqistudent/lab
RUN chown -R luqistudent:luqistudent /home/luqistudent

USER luqistudent

# Container stays alive awaiting commands via the WebSocket terminal router
CMD ["sleep", "infinity"]
