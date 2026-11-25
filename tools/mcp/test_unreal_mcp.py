
import asyncio
import json
from collections import defaultdict
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MCP_URL = "http://127.0.0.1:8000/mcp"

MESH = "/Game/FBX/Skeletal_Mesh/SM_Rat.SM_Rat"

OUTPUT_FILE = Path("tools/mcp/SM_Rat_hierarchy.txt")


# --------------------------------------------------
# MCP response parsing
# --------------------------------------------------

def parse_result(result):
    """Extract JSON data from an MCP tool response."""

    for item in result.content:
        if not hasattr(item, "text"):
            continue

        try:
            return json.loads(item.text)
        except json.JSONDecodeError:
            continue

    raise RuntimeError("Could not parse MCP response as JSON.")


async def call_unreal_tool(session, tool_name, arguments):
    """Call a tool exposed by Unreal MCP."""

    result = await session.call_tool(
        "call_tool",
        arguments={
            "toolset_name": "EditorToolset.SkeletalMeshToolset",
            "tool_name": tool_name,
            "arguments": arguments,
        },
    )

    if result.is_error:
        raise RuntimeError(
            f"Unreal MCP tool failed: {tool_name}"
        )

    return parse_result(result)


# --------------------------------------------------
# Retrieve all bone names
# --------------------------------------------------

async def get_bone_names(session):

    print("\nRetrieving bone names...")

    data = await call_unreal_tool(
        session,
        "GetBoneNames",
        {
            "mesh": {"refPath": MESH}
        },
    )

    bones = data.get("returnValue")

    if not bones:
        raise RuntimeError(
            "No bones returned. Check the skeletal mesh path."
        )

    # Handle Unreal's returned bone structures.
    bone_names = []

    for bone in bones:

        if isinstance(bone, str):
            bone_names.append(bone)

        elif isinstance(bone, dict):
            name = bone.get("BoneName") or bone.get("boneName")

            if name:
                bone_names.append(name)

    if not bone_names:
        raise RuntimeError(
            "Could not extract bone names from MCP response."
        )

    print(f"Found {len(bone_names)} bones.")

    return bone_names


# --------------------------------------------------
# Retrieve parent of every bone
# --------------------------------------------------

async def get_bone_parents(session, bone_names):

    parents = {}

    print("\nRetrieving parent relationships...")

    for index, bone_name in enumerate(bone_names, start=1):

        data = await call_unreal_tool(
            session,
            "GetBoneParent",
            {
                "mesh": {"refPath": MESH},
                "boneName": bone_name,
            },
        )

        parent = data.get("returnValue", "")

        if isinstance(parent, dict):
            parent = parent.get("BoneName", "")

        parents[bone_name] = parent or None

        print(
            f"[{index}/{len(bone_names)}] "
            f"{bone_name} <- {parent or '[ROOT]'}"
        )

    return parents


# --------------------------------------------------
# Build parent-child tree
# --------------------------------------------------

def build_tree(bone_names, parents):

    children = defaultdict(list)

    for bone_name in bone_names:

        parent = parents.get(bone_name)

        if parent:
            children[parent].append(bone_name)

    roots = [
        bone for bone in bone_names
        if not parents.get(bone)
    ]

    return roots, children


# --------------------------------------------------
# Print hierarchy
# --------------------------------------------------

def format_tree(roots, children):

    lines = []

    def walk(bone_name, prefix="", is_last=True):

        connector = "└── " if is_last else "├── "

        lines.append(prefix + connector + bone_name)

        child_bones = children.get(bone_name, [])

        next_prefix = prefix + (
            "    " if is_last else "│   "
        )

        for index, child in enumerate(child_bones):

            walk(
                child,
                next_prefix,
                index == len(child_bones) - 1,
            )

    for index, root in enumerate(roots):

        if index > 0:
            lines.append("")

        lines.append(root)

        root_children = children.get(root, [])

        for child_index, child in enumerate(root_children):

            walk(
                child,
                "",
                child_index == len(root_children) - 1,
            )

    return "\n".join(lines)


# --------------------------------------------------
# Main
# --------------------------------------------------

async def main():

    print("=" * 60)
    print("SM_Rat Skeleton Hierarchy Retrieval")
    print("=" * 60)

    print(f"\nMesh: {MESH}")
    print(f"MCP:  {MCP_URL}")

    async with streamable_http_client(MCP_URL) as (
        read_stream,
        write_stream
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            print("\nMCP connection initialized.")

            # Step 1: Retrieve bone names
            bone_names = await get_bone_names(session)

            # Step 2: Retrieve parent of every bone
            parents = await get_bone_parents(
                session,
                bone_names
            )

            # Step 3: Construct hierarchy
            roots, children = build_tree(
                bone_names,
                parents
            )

            # Step 4: Format hierarchy
            hierarchy = format_tree(
                roots,
                children
            )

            # Step 5: Display hierarchy
            print("\n")
            print("=" * 60)
            print("COMPLETE SM_Rat PARENT-CHILD HIERARCHY")
            print("=" * 60)

            print(hierarchy)

            # Step 6: Save output
            OUTPUT_FILE.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with OUTPUT_FILE.open(
                "w",
                encoding="utf-8"
            ) as file:

                file.write(
                    f"Mesh: {MESH}\n\n"
                )

                file.write(hierarchy)

                file.write("\n")

            # Step 7: Summary
            print("\n")
            print("=" * 60)
            print("RETRIEVAL SUMMARY")
            print("=" * 60)

            print(f"Total bones: {len(bone_names)}")
            print(f"Root bones:  {len(roots)}")
            print(f"Output:      {OUTPUT_FILE.resolve()}")

            if len(parents) != len(bone_names):
                print("WARNING: Some parent relationships are missing.")

            print("\nHierarchy retrieval completed.")


if __name__ == "__main__":
    asyncio.run(main())
