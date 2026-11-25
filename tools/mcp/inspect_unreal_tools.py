import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("http://127.0.0.1:8000/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "describe_toolsets",
                arguments={
                    "toolset_names": [
                        "EditorToolset.SkeletalMeshToolset",
                        "EditorToolset.ActorToolset"
                    ]
                }
            )

            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)

if __name__ == "__main__":
    asyncio.run(main())