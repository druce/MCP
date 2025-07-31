"""
This module implements a simple MCP server using FastMCP,
providing a tool unladen_swallow_airspeed, returns a string based on input swallow type
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("swallow-server")


@mcp.tool()
def unladen_swallow_airspeed(swallow_type: str) -> str:
    """Provides the airspeed velocity of an unladen swallow. Takes a 'swallow_type' argument ('african' or 'european')."""
    stype = swallow_type.strip().lower()
    if stype == 'african':
        return "31.1415926 km/h"
    elif stype == 'european':
        return "27.1828km/h"
    else:
        return "I don't know!"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
