# SaltStack API MCP Server

A Model Context Protocol (MCP) server that provides secure access to SaltStack salt-api for managing Salt minions.

## Purpose

This MCP server provides a secure interface for AI assistants to interact with SaltStack infrastructure through salt-api, enabling minion management and command execution.

## Features

### Current Implementation

- **`list_all_minions`** - List all Salt minions with their online/offline status
- **`ping_minions`** - Test connectivity to minions using test.ping (default target: *)  
- **`get_minion_info`** - Get detailed system information about a specific minion
- **`execute_salt_command`** - Execute arbitrary Salt functions on specified minions

## Prerequisites

- Docker Desktop with MCP Toolkit enabled
- Docker MCP CLI plugin (`docker mcp` command)
- SaltStack Master with salt-api enabled and running
- Salt API authentication configured (PAM auth recommended)

## Salt API Setup

### 1. Install salt-api on your Salt Master

```bash
# CentOS/RHEL
sudo yum install salt-api

# Ubuntu/Debian  
sudo apt-get install salt-api

# Install CherryPy (recommended web server)
pip install CherryPy
```

### 2. Configure salt-api

Edit `/etc/salt/master` and add:

```yaml
rest_cherrypy:
  port: 8000
  host: 0.0.0.0
  disable_ssl: true  # Use SSL in production!

external_auth:
  pam:
    saltapi:
      - .*
      - '@wheel'
      - '@runner'
```

### 3. Create salt-api user

```bash
# Create system user for salt-api
sudo useradd saltapi
sudo passwd saltapi

# Add to salt group
sudo usermod -a -G salt saltapi
```

### 4. Start salt-api service

```bash
sudo systemctl restart salt-master
sudo systemctl start salt-api
sudo systemctl enable salt-api
```

## Installation

See the step-by-step instructions provided with the files.

## Usage Examples

In Claude Desktop, you can ask:

- "Show me all Salt minions and their status"
- "Ping all minions to check connectivity" 
- "Get detailed info about minion web01"
- "Check disk space on all web servers"
- "Restart nginx service on minion web01"
- "Run 'uptime' command on all Linux minions"

## Architecture

```
Claude Desktop → MCP Gateway → SaltStack API MCP Server → salt-api → Salt Master → Minions
                                         ↓
                               Docker Desktop Secrets
                              (SALT_API_USERNAME, SALT_API_PASSWORD)
```

## Security Configuration

The server uses the following environment variables:

- `SALT_API_URL` - Salt API endpoint (default: http://host.docker.internal:8000)
- `SALT_API_USERNAME` - Username for salt-api authentication  
- `SALT_API_PASSWORD` - Password for salt-api authentication

## Development

### Local Testing

```bash
# Set environment variables for testing
export SALT_API_URL="http://localhost:8000"
export SALT_API_USERNAME="saltapi"
export SALT_API_PASSWORD="your-password"

# Run directly
python saltapi_server.py

# Test MCP protocol
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python saltapi_server.py
```

### Adding New Tools

1. Add the function to `saltapi_server.py`
2. Decorate with `@mcp.tool()`
3. Update the catalog entry with the new tool name
4. Rebuild the Docker image

## Troubleshooting

### Tools Not Appearing

- Verify Docker image built successfully
- Check catalog and registry files
- Ensure Claude Desktop config includes custom catalog
- Restart Claude Desktop

### Authentication Errors

- Verify salt-api is running: `curl http://localhost:8000`
- Test authentication: `curl -k http://localhost:8000/login -d '{"username":"saltapi","password":"yourpass","eauth":"pam"}' -H "Content-Type: application/json"`
- Check salt-api logs: `sudo journalctl -u salt-api -f`
- Verify secrets with `docker mcp secret list`

### Connection Issues

- Ensure salt-api is accessible from Docker container
- Check firewall rules for port 8000
- Verify `host.docker.internal` resolves (Windows/Mac) or use actual IP
- Check Salt Master is running: `sudo systemctl status salt-master`

## Common Salt Commands

- `test.ping` - Test minion connectivity
- `cmd.run` - Execute shell commands
- `service.status` - Check service status
- `pkg.list_upgrades` - List available package updates
- `disk.usage` - Check disk usage
- `grains.items` - Get system information

## Security Considerations

- All credentials stored in Docker Desktop secrets
- Never hardcode authentication details
- Running as non-root user
- Consider enabling SSL for salt-api in production
- Limit salt-api user permissions appropriately

## License

MIT License
