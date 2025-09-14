# SaltStack MCP server

## Setup

### Requirement
- Docker
- Docker MCP Gateway
- MCP Client

### Step 1: Build Docker Image

```
docker build -t saltapi-mcp-server 
```

### Step 2: Set Up Secrets

```
# Set your Salt API credentials
secret set SALT_API_USERNAME="saltapi"
docker mcp secret set SALT_API_PASSWORD="your-password"

# Optional: Set custom salt-api URL (defaults to http://host.docker.internal:8000)
docker mcp secret set SALT_API_URL="http://your-salt-master:8000"

# Verify secrets
docker mcp secret list
```

### Step 3: Create Custom Catalogue

custom.yaml
```
version: 2
name: custom
displayName: Custom MCP Servers
registry:
  saltapi:
    description: "SaltStack API integration for managing Salt minions"
    title: "SaltStack API"
    type: server
    dateAdded: "2025-09-14T00:00:00Z"
    image: saltapi-mcp-server:latest
    ref: ""
    readme: ""
    toolsUrl: ""
    source: ""
    upstream: ""
    icon: ""
    tools:
      - name: list_all_minions
      - name: ping_minions
      - name: get_minion_info
      - name: execute_salt_command
    secrets:
      - name: SALT_API_USERNAME
        env: SALT_API_USERNAME
        example: saltapi
      - name: SALT_API_PASSWORD
        env: SALT_API_PASSWORD
        example: your-secure-password
      - name: SALT_API_URL
        env: SALT_API_URL
        example: http://host.docker.internal:8000
    metadata:
      category: automation
      tags:
        - saltstack
        - infrastructure
        - devops
        - automation
      license: MIT
      owner: local
```

### Step 4: Add to registry

```
registry:
  # ... existing servers ...
  saltapi:
    ref: ""
```





