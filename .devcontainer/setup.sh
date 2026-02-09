#!/bin/bash
set -e

# Remove Yarn repo if present (missing GPG key)
sudo rm -f /etc/apt/sources.list.d/yarn.list

# Update and install npm
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y npm

# Install uv for python tool management
if ! command -v uv &> /dev/null; then
    pip install uv
fi

# Install GitHub Copilot CLI globally
sudo npm install -g @github/copilot

# Install Spec-Kit tool
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git --force