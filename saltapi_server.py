#!/usr/bin/env python3
"""
Simple SaltStack API MCP Server - Manage Salt minions via salt-api
"""
import os
import sys
import logging
import json
from datetime import datetime, timezone
import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("saltapi-server")

# Initialize MCP server - NO PROMPT PARAMETER!
mcp = FastMCP("saltapi")

# Configuration for PAM Authentication
SALT_API_URL = os.environ.get("SALT_API_URL", "http://host.docker.internal:8000")
SALT_API_USERNAME = os.environ.get("SALT_API_USERNAME", "")
SALT_API_PASSWORD = os.environ.get("SALT_API_PASSWORD", "")

# === UTILITY FUNCTIONS ===

async def get_salt_token():
    """Authenticate with salt-api and get token."""
    if not SALT_API_USERNAME or not SALT_API_PASSWORD:
        return None, "Salt API credentials not configured"

    auth_data = {
        "username": SALT_API_USERNAME,
        "password": SALT_API_PASSWORD,
        "eauth": "pam"  # Default external auth
    }

    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{SALT_API_URL}/login",
                json=auth_data,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            token = data.get("return", [{}])[0].get("token", "")
            return token, None
    except httpx.HTTPStatusError as e:
        return None, f"Authentication failed: {e.response.status_code}"
    except Exception as e:
        return None, f"Authentication error: {str(e)}"

async def salt_api_request(endpoint, data=None, token=None):
    """Make authenticated request to salt-api."""
    headers = {}
    if token:
        headers["X-Auth-Token"] = token

    try:
        async with httpx.AsyncClient(verify=False) as client:
            if data:
                response = await client.post(
                    f"{SALT_API_URL}{endpoint}",
                    headers=headers,
                    json=data,
                    timeout=30
                )
            else:
                response = await client.get(
                    f"{SALT_API_URL}{endpoint}",
                    headers=headers,
                    timeout=30
                )
            response.raise_for_status()
            return response.json(), None
    except httpx.HTTPStatusError as e:
        return None, f"API Error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return None, f"Request error: {str(e)}"

# === MCP TOOLS ===

@mcp.tool()
async def list_all_minions() -> str:
    """List all Salt minions registered with the Salt master."""
    logger.info("Executing list_all_minions")

    try:
        token, auth_error = await get_salt_token()
        if auth_error:
            return f"❌ Authentication Error: {auth_error}"

        # Get minion list using salt-run manage.list_all
        data = {
            "client": "runner",
            "fun": "manage.status"
        }
        result, error = await salt_api_request("/", data, token)
        if error:
            return f"❌ API Error: {error}"

        if not result or not result.get("return"):
            return "❌ Error: No data returned from Salt API"

        minion_data = result["return"][0]

        # Format the response
        output = ["📊 Salt Minions Status:\n"]

        # Online minions
        up_minions = minion_data.get("up", [])
        if up_minions:
            output.append(f"✅ Online Minions ({len(up_minions)}):")
            for minion in sorted(up_minions):
                output.append(f"  • {minion}")
            output.append("")

        # Offline minions
        down_minions = minion_data.get("down", [])
        if down_minions:
            output.append(f"❌ Offline Minions ({len(down_minions)}):")
            for minion in sorted(down_minions):
                output.append(f"  • {minion}")
            output.append("")

        # Summary
        total = len(up_minions) + len(down_minions)
        output.append(f"📈 Summary: {len(up_minions)} online, {len(down_minions)} offline, {total} total")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def ping_minions(target: str = "*") -> str:
    """Test connectivity to Salt minions using test.ping function."""
    logger.info(f"Executing ping_minions with target: {target}")

    if not target.strip():
        target = "*"

    try:
        token, auth_error = await get_salt_token()
        if auth_error:
            return f"❌ Authentication Error: {auth_error}"

        # Execute test.ping on minions
        data = {
            "client": "local",
            "tgt": target,
            "fun": "test.ping"
        }

        result, error = await salt_api_request("/", data, token)
        if error:
            return f"❌ API Error: {error}"

        if not result or not result.get("return"):
            return "❌ Error: No data returned from Salt API"

        ping_results = result["return"][0]

        # Format the response
        output = [f"🔍 Ping Results for target '{target}':\n"]

        if not ping_results:
            output.append("⚠️ No minions matched the target or responded")
            return "\n".join(output)

        responding = []
        not_responding = []

        for minion, response in ping_results.items():
            if response is True:
                responding.append(minion)
            else:
                not_responding.append((minion, response))

        # Show responding minions
        if responding:
            output.append(f"✅ Responding Minions ({len(responding)}):")
            for minion in sorted(responding):
                output.append(f"  • {minion} - Online")
            output.append("")

        # Show non-responding minions
        if not_responding:
            output.append(f"❌ Non-responding Minions ({len(not_responding)}):")
            for minion, response in not_responding:
                output.append(f"  • {minion} - {response}")
            output.append("")

        # Summary
        total_targeted = len(ping_results)
        output.append(f"📊 Summary: {len(responding)} responding, {len(not_responding)} not responding, {total_targeted} total targeted")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def get_minion_info(minion_id: str = "") -> str:
    """Get detailed information about a specific Salt minion."""
    logger.info(f"Executing get_minion_info for minion: {minion_id}")

    if not minion_id.strip():
        return "❌ Error: Minion ID is required"

    try:
        token, auth_error = await get_salt_token()
        if auth_error:
            return f"❌ Authentication Error: {auth_error}"

        # Get minion grains (system information)
        data = {
            "client": "local",
            "tgt": minion_id,
            "fun": "grains.items"
        }

        result, error = await salt_api_request("/", data, token)
        if error:
            return f"❌ API Error: {error}"

        if not result or not result.get("return") or not result["return"][0]:
            return f"❌ Error: Minion '{minion_id}' not found or not responding"

        grains = result["return"][0].get(minion_id)
        if not grains:
            return f"❌ Error: No data available for minion '{minion_id}'"

        # Format key information
        output = [f"🖥️ Minion Information: {minion_id}\n"]

        # Basic system info
        output.append("💻 System Information:")
        output.append(f"  • OS: {grains.get('os', 'Unknown')} {grains.get('osrelease', '')}")
        output.append(f"  • Architecture: {grains.get('osarch', 'Unknown')}")
        output.append(f"  • Kernel: {grains.get('kernel', 'Unknown')}")
        output.append(f"  • Hostname: {grains.get('fqdn', grains.get('id', 'Unknown'))}")
        output.append("")

        # Hardware info
        if grains.get('num_cpus') or grains.get('mem_total'):
            output.append("⚡ Hardware:")
            if grains.get('num_cpus'):
                output.append(f"  • CPUs: {grains['num_cpus']}")
            if grains.get('mem_total'):
                mem_gb = round(grains['mem_total'] / 1024, 1)
                output.append(f"  • Memory: {mem_gb} GB")
            output.append("")

        # Network info
        if grains.get('ip4_interfaces') or grains.get('ipv4'):
            output.append("🌐 Network:")
            if grains.get('ipv4'):
                for ip in grains['ipv4']:
                    if ip != '127.0.0.1':
                        output.append(f"  • IP: {ip}")
            output.append("")

        # Salt info
        output.append("🧂 Salt Information:")
        output.append(f"  • Salt Version: {grains.get('saltversion', 'Unknown')}")
        output.append(f"  • Master: {grains.get('master', 'Unknown')}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def execute_salt_command(target: str = "*", function: str = "", args: str = "") -> str:
    """Execute a Salt function on specified minions."""
    logger.info(f"Executing salt command: {function} on {target}")

    if not target.strip():
        target = "*"

    if not function.strip():
        return "❌ Error: Salt function is required (e.g., 'cmd.run', 'service.status')"

    try:
        token, auth_error = await get_salt_token()
        if auth_error:
            return f"❌ Authentication Error: {auth_error}"

        # Prepare the salt command
        data = {
            "client": "local",
            "tgt": target,
            "fun": function
        }

        # Add arguments if provided
        if args.strip():
            # Try to parse args as JSON array, fallback to single argument
            try:
                parsed_args = json.loads(args)
                if isinstance(parsed_args, list):
                    data["arg"] = parsed_args
                else:
                    data["arg"] = [str(parsed_args)]
            except json.JSONDecodeError:
                data["arg"] = [args]

        result, error = await salt_api_request("/", data, token)
        if error:
            return f"❌ API Error: {error}"

        if not result or not result.get("return"):
            return "❌ Error: No data returned from Salt API"

        command_results = result["return"][0]

        # Format the response
        output = [f"⚡ Salt Command Results: {function}\n"]
        output.append(f"🎯 Target: {target}")
        if args.strip():
            output.append(f"📝 Arguments: {args}")
        output.append("")

        if not command_results:
            output.append("⚠️ No minions matched the target or responded")
            return "\n".join(output)

        # Show results for each minion
        for minion, minion_result in command_results.items():
            output.append(f"📍 {minion}:")
            if isinstance(minion_result, (dict, list)):
                output.append(f"  {json.dumps(minion_result, indent=2)}")
            else:
                # Handle multiline output
                result_str = str(minion_result)
                if '\n' in result_str:
                    lines = result_str.split('\n')
                    for line in lines[:20]:  # Limit output
                        output.append(f"  {line}")
                    if len(lines) > 20:
                        output.append(f"  ... ({len(lines) - 20} more lines)")
                else:
                    output.append(f"  {result_str}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

# === SERVER STARTUP ===
if __name__ == "__main__":
    logger.info("Starting SaltStack API MCP server...")

    # Startup checks
    if not SALT_API_URL:
        logger.warning("SALT_API_URL not set, using default: http://host.docker.internal:8000")

    if not SALT_API_USERNAME or not SALT_API_PASSWORD:
        logger.warning("SALT_API_USERNAME or SALT_API_PASSWORD not set - authentication may fail")
    logger.info("Hello")

    # Optional: test token at startup
    import asyncio
    try:
        output = asyncio.run(list_all_minions())
        logger.info(f"Initial minion list output:\n{output}")
    except Exception as e:
        logger.error(f"Token test failed: {e}")

    try:
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
