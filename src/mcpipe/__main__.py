"""CLI entrypoint for mcpipe."""

import asyncio
import sys

from mcpipe.cli import main


def mcp(transport: str = "stdio") -> None:
    """Entry point for setuptools console_scripts."""
    from mcpipe.server import serve

    match transport:
        case "stdio":
            asyncio.run(serve())
        case _:
            print(
                f"Error: unknown transport '{transport}'",
                file=sys.stderr,
            )
            sys.exit(1)


def cli() -> None:
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli()
