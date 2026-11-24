from mcp.server import MCPServer

mcp = MCPServer("task7-demo")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers and return the result."""
    return a + b


if __name__ == "__main__":
    mcp.run(transport="stdio")
