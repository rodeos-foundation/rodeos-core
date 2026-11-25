import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client('http://127.0.0.1:8000/mcp') as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            ts = await s.call_tool('list_toolsets', {})
            text = "\n".join(getattr(i, 'text', '') for i in ts.content if getattr(i, 'text', ''))
            names = []
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    names.append(line[2:].split(":", 1)[0].strip())
            print("COUNT:", len(names))
            print("NAMES:", names)
            for i in range(0, len(names), 10):
                batch = names[i:i+10]
                desc = await s.call_tool('describe_toolsets', {'toolset_names': batch, 'include_tools': True})
                for item in desc.content:
                    if getattr(item, 'text', ''):
                        print(item.text)

asyncio.run(main())