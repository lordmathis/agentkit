#!/bin/bash

if [ -n "$1" ]; then
    GITEA_MCP_VERSION="$1"
else
    GITEA_MCP_VERSION=$(curl -s https://gitea.com/api/v1/repos/gitea/gitea-mcp/releases/latest | grep -oP '"tag_name":\s*"\K[^"]+')
fi

ORIGINAL_DIR=$(pwd)
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
curl -L https://gitea.com/gitea/gitea-mcp/releases/download/${GITEA_MCP_VERSION}/gitea-mcp_Linux_x86_64.tar.gz | tar -xzvf -
mv gitea-mcp "$ORIGINAL_DIR/"
cd "$ORIGINAL_DIR"
rm -rf "$TEMP_DIR"
chmod +x gitea-mcp