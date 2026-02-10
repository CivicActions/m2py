#!/bin/bash
set -e

# Set ownership on /workspaces
sudo chown -R vscode:vscode /workspaces

# Install Spec-Kit tool
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git --force