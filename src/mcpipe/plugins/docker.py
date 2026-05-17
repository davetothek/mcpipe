"""Docker plugin for mcpipe."""

from __future__ import annotations

from typing import Annotated

from mcpipe import Cmd, tool
from mcpipe.transform import TransformStep


@tool(
    "List running containers",
    read_only=True,
    destructive=False,
    idempotent=True,
)
def docker_ps(
    all: Annotated[bool, "Show all containers (including stopped)"] = False,
    format: Annotated[str, "Go template for output format"] = "",
) -> Cmd:
    args = ["docker", "ps"]
    if all:
        args.append("--all")
    if format:
        args.extend(["--format", format])
    return Cmd(*args)


@tool(
    "Show container logs",
    read_only=True,
    destructive=False,
    idempotent=True,
)
def docker_logs(
    container: Annotated[str, "Container name or ID"],
    tail: Annotated[int, "Number of lines from the end"] = 100,
    since: Annotated[str, "Show logs since timestamp (e.g. '1h', '2024-01-01')"] = "",
) -> Cmd:
    args = ["docker", "logs", f"--tail={tail}"]
    if since:
        args.extend(["--since", since])
    args.append(container)
    return Cmd(*args)


@tool(
    "List Docker images",
    read_only=True,
    destructive=False,
    idempotent=True,
)
def docker_images(
    filter: Annotated[str, "Filter by reference (e.g. 'nginx')"] = "",
) -> Cmd:
    args = ["docker", "images"]
    if filter:
        args.append(filter)
    return Cmd(*args)


# --- Docker Compose tools ---


def _compose_base(file: str = "", project: str = "") -> list[str]:
    """Build the common docker compose prefix."""
    args = ["docker", "compose"]
    if file:
        args.extend(["-f", file])
    if project:
        args.extend(["-p", project])
    return args


@tool(
    "List compose services and their status",
    read_only=True,
    destructive=False,
    idempotent=True,
)
def compose_ps(
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    all: Annotated[bool, "Show all services (including stopped)"] = False,
    format: Annotated[str, "Go template for output format"] = "",
) -> Cmd:
    args = _compose_base(file, project) + ["ps"]
    if all:
        args.append("--all")
    if format:
        args.extend(["--format", format])
    return Cmd(*args)


@tool(
    "View logs from compose services",
    read_only=True,
    destructive=False,
    idempotent=True,
)
def compose_logs(
    service: Annotated[str, "Service name (omit for all services)"] = "",
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    tail: Annotated[int, "Number of lines from the end"] = 100,
    since: Annotated[str, "Show logs since timestamp (e.g. '1h', '2024-01-01')"] = "",
    follow: Annotated[bool, "Follow log output"] = False,
    timestamps: Annotated[bool, "Show timestamps"] = False,
) -> Cmd:
    args = _compose_base(file, project) + ["logs", f"--tail={tail}"]
    if since:
        args.extend(["--since", since])
    if follow:
        args.append("--follow")
    if timestamps:
        args.append("--timestamps")
    if service:
        args.append(service)
    return Cmd(*args)


@tool(
    "Start compose services",
    read_only=False,
    destructive=False,
    idempotent=True,
    output_filter=[TransformStep("tail", {"n": 10})],
)
def compose_up(
    service: Annotated[str, "Service name (omit for all services)"] = "",
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    detach: Annotated[bool, "Run in background"] = True,
    build: Annotated[bool, "Build images before starting"] = False,
    force_recreate: Annotated[bool, "Recreate containers even if unchanged"] = False,
    remove_orphans: Annotated[bool, "Remove containers for undefined services"] = False,
) -> Cmd:
    args = _compose_base(file, project) + ["up"]
    if detach:
        args.append("--detach")
    if build:
        args.append("--build")
    if force_recreate:
        args.append("--force-recreate")
    if remove_orphans:
        args.append("--remove-orphans")
    if service:
        args.append(service)
    return Cmd(*args)


@tool(
    "Stop and remove compose services",
    read_only=False,
    destructive=True,
    idempotent=True,
    output_filter=[TransformStep("tail", {"n": 10})],
)
def compose_down(
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    volumes: Annotated[bool, "Remove named volumes"] = False,
    remove_orphans: Annotated[bool, "Remove containers for undefined services"] = False,
    rmi: Annotated[str, "Remove images: 'all' or 'local'"] = "",
) -> Cmd:
    args = _compose_base(file, project) + ["down"]
    if volumes:
        args.append("--volumes")
    if remove_orphans:
        args.append("--remove-orphans")
    if rmi:
        args.extend(["--rmi", rmi])
    return Cmd(*args)


@tool(
    "Restart compose services",
    read_only=False,
    destructive=False,
    idempotent=True,
    output_filter=[TransformStep("tail", {"n": 10})],
)
def compose_restart(
    service: Annotated[str, "Service name (omit for all services)"] = "",
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    timeout: Annotated[int, "Shutdown timeout in seconds"] = 0,
) -> Cmd:
    args = _compose_base(file, project) + ["restart"]
    if timeout:
        args.extend(["--timeout", str(timeout)])
    if service:
        args.append(service)
    return Cmd(*args)


@tool(
    "Stop compose services without removing them",
    read_only=False,
    destructive=False,
    idempotent=True,
    output_filter=[TransformStep("tail", {"n": 10})],
)
def compose_stop(
    service: Annotated[str, "Service name (omit for all services)"] = "",
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    timeout: Annotated[int, "Shutdown timeout in seconds"] = 0,
) -> Cmd:
    args = _compose_base(file, project) + ["stop"]
    if timeout:
        args.extend(["--timeout", str(timeout)])
    if service:
        args.append(service)
    return Cmd(*args)


@tool(
    "Start existing stopped compose services",
    read_only=False,
    destructive=False,
    idempotent=True,
    output_filter=[TransformStep("tail", {"n": 10})],
)
def compose_start(
    service: Annotated[str, "Service name (omit for all services)"] = "",
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
) -> Cmd:
    args = _compose_base(file, project) + ["start"]
    if service:
        args.append(service)
    return Cmd(*args)


@tool(
    "Validate and view resolved compose config",
    read_only=True,
    destructive=False,
    idempotent=True,
)
def compose_config(
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    services: Annotated[bool, "Print only service names"] = False,
    volumes: Annotated[bool, "Print only volume names"] = False,
) -> Cmd:
    args = _compose_base(file, project) + ["config"]
    if services:
        args.append("--services")
    if volumes:
        args.append("--volumes")
    return Cmd(*args)


@tool(
    "Show running processes in compose services",
    read_only=True,
    destructive=False,
    idempotent=True,
)
def compose_top(
    service: Annotated[str, "Service name (omit for all services)"] = "",
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
) -> Cmd:
    args = _compose_base(file, project) + ["top"]
    if service:
        args.append(service)
    return Cmd(*args)


@tool(
    "List images used by compose services",
    read_only=True,
    destructive=False,
    idempotent=True,
)
def compose_images(
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
) -> Cmd:
    return Cmd(*_compose_base(file, project), "images")


@tool(
    "Pull compose service images",
    read_only=False,
    destructive=False,
    idempotent=True,
    output_filter=[TransformStep("tail", {"n": 10})],
)
def compose_pull(
    service: Annotated[str, "Service name (omit for all services)"] = "",
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    quiet: Annotated[bool, "Suppress progress output"] = False,
) -> Cmd:
    args = _compose_base(file, project) + ["pull"]
    if quiet:
        args.append("--quiet")
    if service:
        args.append(service)
    return Cmd(*args)


@tool(
    "Build or rebuild compose services",
    read_only=False,
    destructive=False,
    idempotent=True,
    output_filter=[TransformStep("tail", {"n": 10})],
)
def compose_build(
    service: Annotated[str, "Service name (omit for all services)"] = "",
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    no_cache: Annotated[bool, "Do not use cache when building"] = False,
    pull: Annotated[bool, "Always pull newer image versions"] = False,
) -> Cmd:
    args = _compose_base(file, project) + ["build"]
    if no_cache:
        args.append("--no-cache")
    if pull:
        args.append("--pull")
    if service:
        args.append(service)
    return Cmd(*args)


@tool(
    "Execute a command in a running compose service container",
    read_only=False,
    destructive=False,
    idempotent=False,
)
def compose_exec(
    service: Annotated[str, "Service name"],
    command: Annotated[str, "Command to execute"],
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    user: Annotated[str, "Run as this user"] = "",
    workdir: Annotated[str, "Working directory inside container"] = "",
) -> Cmd:
    args = _compose_base(file, project) + ["exec", "--no-TTY"]
    if user:
        args.extend(["--user", user])
    if workdir:
        args.extend(["--workdir", workdir])
    args.append(service)
    args.extend(command.split())
    return Cmd(*args)


@tool(
    "Run a one-off command in a new compose service container",
    read_only=False,
    destructive=False,
    idempotent=False,
)
def compose_run(
    service: Annotated[str, "Service name"],
    command: Annotated[str, "Command to execute"] = "",
    file: Annotated[str, "Path to compose file"] = "",
    project: Annotated[str, "Project name"] = "",
    rm: Annotated[bool, "Remove container after run"] = True,
    no_deps: Annotated[bool, "Don't start linked services"] = False,
    user: Annotated[str, "Run as this user"] = "",
) -> Cmd:
    args = _compose_base(file, project) + ["run", "--no-TTY"]
    if rm:
        args.append("--rm")
    if no_deps:
        args.append("--no-deps")
    if user:
        args.extend(["--user", user])
    args.append(service)
    if command:
        args.extend(command.split())
    return Cmd(*args)
