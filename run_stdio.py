#!/usr/bin/env python3
"""
Stdio wrapper for Nextcloud MCP Server (v0.68.x)
Enables stdio transport for use with Claude Desktop.

This bypasses the HTTP-based transports and directly runs the FastMCP server
with stdio, reading JSON-RPC messages from stdin and writing to stdout.
"""

import anyio
import sys
import logging
import os

# Configure logging to stderr ONLY (stdout is reserved for JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
    force=True
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

async def main():
    """Run the Nextcloud MCP server with stdio transport"""
    try:
        logger.info("Starting Nextcloud MCP server with stdio transport (v0.68.x)")
        logger.info(f"NEXTCLOUD_HOST: {os.getenv('NEXTCLOUD_HOST')}")
        logger.info(f"NEXTCLOUD_USERNAME: {os.getenv('NEXTCLOUD_USERNAME')}")

        from nextcloud_mcp_server.config import get_settings
        from nextcloud_mcp_server.app import app_lifespan_basic
        from nextcloud_mcp_server.context import get_client as get_nextcloud_client
        from nextcloud_mcp_server.server import (
            configure_calendar_tools,
            configure_collectives_tools,
            configure_contacts_tools,
            configure_cookbook_tools,
            configure_deck_tools,
            configure_news_tools,
            configure_notes_tools,
            configure_semantic_tools,
            configure_sharing_tools,
            configure_tables_tools,
            configure_webdav_tools,
        )
        from mcp.server.fastmcp import FastMCP, Context

        # stdio transport always uses BasicAuth (no OAuth support)
        logger.info("Configuring MCP server for BasicAuth mode with stdio")
        settings = get_settings()

        # Create FastMCP instance with BasicAuth lifespan
        mcp = FastMCP("Nextcloud MCP", lifespan=app_lifespan_basic)

        @mcp.resource("nc://capabilities")
        async def nc_get_capabilities():
            """Get the Nextcloud Host capabilities"""
            ctx: Context = mcp.get_context()
            client = await get_nextcloud_client(ctx)
            return await client.capabilities()

        # Configure all available app tools
        available_apps = {
            "notes": configure_notes_tools,
            "tables": configure_tables_tools,
            "webdav": configure_webdav_tools,
            "sharing": configure_sharing_tools,
            "calendar": configure_calendar_tools,
            "collectives": configure_collectives_tools,
            "contacts": configure_contacts_tools,
            "cookbook": configure_cookbook_tools,
            "deck": configure_deck_tools,
            "news": configure_news_tools,
        }

        logger.info("Configuring all Nextcloud app tools")
        for app_name, configure_func in available_apps.items():
            logger.info(f"  - {app_name}")
            configure_func(mcp)

        # Configure semantic search if enabled
        if settings.vector_sync_enabled:
            logger.info("Configuring semantic search tools (vector sync enabled)")
            configure_semantic_tools(mcp)
        else:
            logger.info("Skipping semantic search tools (VECTOR_SYNC_ENABLED not set)")

        logger.info("Running MCP server with stdio transport")
        await mcp.run_stdio_async()

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    anyio.run(main)
