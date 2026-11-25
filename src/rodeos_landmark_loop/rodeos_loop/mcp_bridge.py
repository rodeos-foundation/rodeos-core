import asyncio
import base64
from pathlib import Path
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

class MCPBridge:
    def __init__(self, cfg):
        self.url = cfg["mcp"]["url"]
        self.toolset = cfg["mcp"]["capture_toolset"]
        self.capture_tool = cfg["mcp"]["capture_tool"]
        self.capture_args = cfg["mcp"].get("capture_arguments", {})

    async def capture(self, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with streamable_http_client(self.url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "call_tool",
                    arguments={
                        "toolset_name": self.toolset,
                        "tool_name": self.capture_tool,
                        "arguments": self.capture_args,
                    },
                )
                for item in result.content:
                    data = getattr(item, "data", None)
                    if data:
                        output_path.write_bytes(base64.b64decode(data))
                        return str(output_path)
                messages = [
                    getattr(item, "text", "")
                    for item in result.content
                    if getattr(item, "text", "")
                ]
                raise RuntimeError(
                    "MCP capture returned no image content. Response: " + "\n".join(messages)
                )

    def capture_sync(self, output_path):
        return asyncio.run(self.capture(output_path))
