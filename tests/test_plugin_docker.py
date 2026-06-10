"""Tests for mcpipe.plugins.docker."""

from __future__ import annotations

from mcpipe.plugins.docker import (
    compose_build,
    compose_config,
    compose_down,
    compose_exec,
    compose_images,
    compose_logs,
    compose_ps,
    compose_pull,
    compose_restart,
    compose_run,
    compose_start,
    compose_stop,
    compose_top,
    compose_up,
    docker_images,
    docker_logs,
    docker_ps,
)


def test_docker_ps():
    cmd1 = docker_ps()
    assert cmd1.argv == ["docker", "ps"]

    cmd2 = docker_ps(all=True, format="{{.ID}}")
    assert cmd2.argv == ["docker", "ps", "--all", "--format", "{{.ID}}"]


def test_docker_logs():
    cmd = docker_logs("my-container", tail=50, since="10m")
    assert cmd.argv == ["docker", "logs", "--tail=50", "--since", "10m", "my-container"]


def test_docker_images():
    cmd = docker_images(filter="nginx")
    assert cmd.argv == ["docker", "images", "nginx"]


def test_compose_ps():
    cmd = compose_ps(
        file="docker-compose.yml", project="myproj", all=True, format="json"
    )
    assert cmd.argv == [
        "docker",
        "compose",
        "-f",
        "docker-compose.yml",
        "-p",
        "myproj",
        "ps",
        "--all",
        "--format",
        "json",
    ]


def test_compose_logs():
    cmd = compose_logs(
        service="web",
        file="c.yml",
        project="p",
        tail=200,
        since="1h",
        follow=True,
        timestamps=True,
    )
    assert cmd.argv == [
        "docker",
        "compose",
        "-f",
        "c.yml",
        "-p",
        "p",
        "logs",
        "--tail=200",
        "--since",
        "1h",
        "--follow",
        "--timestamps",
        "web",
    ]


def test_compose_up():
    cmd = compose_up(
        service="db",
        file="c.yml",
        project="p",
        detach=True,
        build=True,
        force_recreate=True,
        remove_orphans=True,
    )
    assert cmd.argv == [
        "docker",
        "compose",
        "-f",
        "c.yml",
        "-p",
        "p",
        "up",
        "--detach",
        "--build",
        "--force-recreate",
        "--remove-orphans",
        "db",
    ]


def test_compose_down():
    cmd = compose_down(
        file="c.yml", project="p", volumes=True, remove_orphans=True, rmi="all"
    )
    assert cmd.argv == [
        "docker",
        "compose",
        "-f",
        "c.yml",
        "-p",
        "p",
        "down",
        "--volumes",
        "--remove-orphans",
        "--rmi",
        "all",
    ]


def test_compose_restart():
    cmd = compose_restart(service="cache", file="c.yml", timeout=30)
    assert cmd.argv == [
        "docker",
        "compose",
        "-f",
        "c.yml",
        "restart",
        "--timeout",
        "30",
        "cache",
    ]


def test_compose_stop():
    cmd = compose_stop(service="app", timeout=10)
    assert cmd.argv == ["docker", "compose", "stop", "--timeout", "10", "app"]


def test_compose_start():
    cmd = compose_start(service="app")
    assert cmd.argv == ["docker", "compose", "start", "app"]


def test_compose_config():
    cmd = compose_config(services=True, volumes=True)
    assert cmd.argv == ["docker", "compose", "config", "--services", "--volumes"]


def test_compose_top():
    cmd = compose_top(service="web")
    assert cmd.argv == ["docker", "compose", "top", "web"]


def test_compose_images():
    cmd = compose_images(project="test")
    assert cmd.argv == ["docker", "compose", "-p", "test", "images"]


def test_compose_pull():
    cmd = compose_pull(service="web", quiet=True)
    assert cmd.argv == ["docker", "compose", "pull", "--quiet", "web"]


def test_compose_build():
    cmd = compose_build(service="web", no_cache=True, pull=True)
    assert cmd.argv == ["docker", "compose", "build", "--no-cache", "--pull", "web"]


def test_compose_exec():
    cmd = compose_exec(
        service="db", command="mysql -uroot", user="root", workdir="/var"
    )
    assert cmd.argv == [
        "docker",
        "compose",
        "exec",
        "--no-TTY",
        "--user",
        "root",
        "--workdir",
        "/var",
        "db",
        "mysql",
        "-uroot",
    ]


def test_compose_run():
    cmd = compose_run(
        service="web", command="npm test", rm=True, no_deps=True, user="node"
    )
    assert cmd.argv == [
        "docker",
        "compose",
        "run",
        "--no-TTY",
        "--rm",
        "--no-deps",
        "--user",
        "node",
        "web",
        "npm",
        "test",
    ]
