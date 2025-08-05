"""
This module implements a simple MCP server using FastMCP,
providing a tool unladen_swallow_airspeed, returns a string based on input swallow type
"""
from mcp.server.fastmcp import FastMCP
from pydantic import Field, BaseModel

class SwallowSpeed(BaseModel):
    speed: str
    unit: str
    swallow_type: str

mcp = FastMCP("swallow-server")

@mcp.tool()
def unladen_swallow_airspeed(
    swallow_type: str = Field(description="Type of swallow: 'african' or 'european'")
) -> SwallowSpeed:
    """Provides the airspeed velocity of an unladen swallow."""
    stype = swallow_type.strip().lower()
    if stype == 'african':
        return SwallowSpeed(speed="31.1415926", unit="km/h", swallow_type="african")
    elif stype == 'european':
        return SwallowSpeed(speed="27.1828", unit="km/h", swallow_type="european")
    else:
        return SwallowSpeed(speed="I don't know!", unit="", swallow_type=stype)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
