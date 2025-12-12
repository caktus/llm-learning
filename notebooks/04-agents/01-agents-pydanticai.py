import asyncio
import sys
from pathlib import Path

from pydantic_ai import Agent
from rich import print

if (
    path := Path(__file__).parent.parent.parent
) not in sys.path:
    print(f"Adding {path} to sys.path")
    sys.path.insert(0, str(path))

from notebooks.pydantic_models import (
    get_model,  # noqa: E402
)

agent = Agent(
    name="Name Cactifier",
    model="openai:gpt-4o-mini",
    instructions="You are a friendly agent that transforms people's names to make them more cactus-like using specific rules.",
)


@agent.tool_plain
def cactify_name(name: str) -> str:
    """Makes a name more cactus-like."""
    base_name = name
    if base_name.lower().endswith(("s", "x")):
        base_name = base_name[:-1]
    if base_name and base_name.lower()[-1] in "aeiou":
        base_name = base_name[:-1]
    return base_name + "actus"


async def main():
    result1 = await agent.run(
        "What would my name, Colin, be if it were cactus-ified?",
        model=get_model(
            "openai:gpt-4o-mini", debug_http=True
        ),
    )
    print("Response:", result1.output)
    print(result1.all_messages())


if __name__ == "__main__":
    asyncio.run(main())
