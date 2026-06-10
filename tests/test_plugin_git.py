"""Tests for mcpipe.plugins.git."""

from __future__ import annotations

import pytest

from mcpipe.plugins.git import (
    _validate_ref,
    git_add,
    git_blame,
    git_branch,
    git_checkout,
    git_cherry_pick,
    git_commit,
    git_create_branch,
    git_diff,
    git_diff_staged,
    git_diff_unstaged,
    git_fetch,
    git_log,
    git_merge,
    git_pull,
    git_push,
    git_remote,
    git_reset,
    git_revert,
    git_show,
    git_stash_list,
    git_stash_pop,
    git_stash_push,
    git_status,
    git_tag,
)


def test_validate_ref():
    _validate_ref("main")  # should not raise
    with pytest.raises(ValueError) as exc:
        _validate_ref("-t")
    assert "cannot start with '-'" in str(exc.value)


def test_git_status():
    cmd = git_status(repo_path="/repo")
    assert cmd.argv == ["git", "-C", "/repo", "status"]


def test_git_log():
    # Defaults
    cmd1 = git_log()
    assert cmd1.argv == ["git", "-C", ".", "log", "--max-count=10"]

    # Custom
    cmd2 = git_log(
        repo_path="/repo",
        max_count=5,
        since="1 week ago",
        until="yesterday",
        path="src/main.py",
    )
    assert cmd2.argv == [
        "git",
        "-C",
        "/repo",
        "log",
        "--max-count=5",
        "--since",
        "1 week ago",
        "--until",
        "yesterday",
        "--",
        "src/main.py",
    ]

    # Flag injection check
    with pytest.raises(ValueError):
        git_log(since="--invalid")
    with pytest.raises(ValueError):
        git_log(until="--invalid")


def test_git_diff_unstaged_and_staged():
    cmd_unstaged = git_diff_unstaged(repo_path="/repo", context_lines=5)
    assert cmd_unstaged.argv == ["git", "-C", "/repo", "diff", "--unified=5"]

    cmd_staged = git_diff_staged(repo_path="/repo", context_lines=2)
    assert cmd_staged.argv == ["git", "-C", "/repo", "diff", "--unified=2", "--cached"]


def test_git_diff():
    cmd = git_diff(repo_path="/repo", target="origin/main", context_lines=4)
    assert cmd.argv == ["git", "-C", "/repo", "diff", "--unified=4", "origin/main"]

    with pytest.raises(ValueError):
        git_diff(target="-f")


def test_git_show():
    cmd = git_show(revision="HEAD~1")
    assert cmd.argv == ["git", "-C", ".", "show", "HEAD~1"]

    with pytest.raises(ValueError):
        git_show(revision="-r")


def test_git_branch():
    # local
    cmd_l = git_branch(branch_type="local", contains="SHA1", not_contains="SHA2")
    assert cmd_l.argv == [
        "git",
        "-C",
        ".",
        "branch",
        "--contains",
        "SHA1",
        "--no-contains",
        "SHA2",
    ]

    # remote
    cmd_r = git_branch(branch_type="remote")
    assert cmd_r.argv == ["git", "-C", ".", "branch", "-r"]

    # all
    cmd_a = git_branch(branch_type="all")
    assert cmd_a.argv == ["git", "-C", ".", "branch", "-a"]

    # invalid branch_type
    with pytest.raises(ValueError):
        git_branch(branch_type="invalid")

    # flag injection
    with pytest.raises(ValueError):
        git_branch(contains="-f")
    with pytest.raises(ValueError):
        git_branch(not_contains="-f")


def test_git_add():
    cmd = git_add(files="a.txt, b.txt")
    assert cmd.argv == ["git", "-C", ".", "add", "--", "a.txt", "b.txt"]


def test_git_commit():
    cmd = git_commit(message="Initial commit")
    assert cmd.argv == ["git", "-C", ".", "commit", "-m", "Initial commit"]

    with pytest.raises(ValueError):
        git_commit(message="")


def test_git_reset():
    cmd = git_reset()
    assert cmd.argv == ["git", "-C", ".", "reset"]


def test_git_create_branch():
    cmd1 = git_create_branch(branch_name="feature", base_branch="main")
    assert cmd1.argv == ["git", "-C", ".", "branch", "feature", "main"]

    cmd2 = git_create_branch(branch_name="feature")
    assert cmd2.argv == ["git", "-C", ".", "branch", "feature"]

    with pytest.raises(ValueError):
        git_create_branch(branch_name="")

    with pytest.raises(ValueError):
        git_create_branch(branch_name="-f")

    with pytest.raises(ValueError):
        git_create_branch(branch_name="feature", base_branch="-f")


def test_git_checkout():
    cmd = git_checkout(branch_name="main")
    assert cmd.argv == ["git", "-C", ".", "checkout", "main"]

    with pytest.raises(ValueError):
        git_checkout(branch_name="")

    with pytest.raises(ValueError):
        git_checkout(branch_name="-f")


def test_git_fetch():
    cmd1 = git_fetch(all=True, prune=True)
    assert cmd1.argv == ["git", "-C", ".", "fetch", "--all", "--prune"]

    cmd2 = git_fetch(remote="origin", prune=True)
    assert cmd2.argv == ["git", "-C", ".", "fetch", "--prune", "origin"]

    with pytest.raises(ValueError):
        git_fetch(remote="-f")


def test_git_pull():
    cmd1 = git_pull(rebase=True)
    assert cmd1.argv == ["git", "-C", ".", "pull", "--rebase"]

    cmd2 = git_pull(remote="origin", branch="main")
    assert cmd2.argv == ["git", "-C", ".", "pull", "origin", "main"]

    with pytest.raises(ValueError):
        git_pull(remote="-f")

    with pytest.raises(ValueError):
        git_pull(remote="origin", branch="-f")


def test_git_push():
    cmd1 = git_push(set_upstream=True, tags=True)
    assert cmd1.argv == ["git", "-C", ".", "push", "-u", "--tags"]

    cmd2 = git_push(remote="origin", branch="main")
    assert cmd2.argv == ["git", "-C", ".", "push", "origin", "main"]

    with pytest.raises(ValueError):
        git_push(remote="-f")

    with pytest.raises(ValueError):
        git_push(remote="origin", branch="-f")


def test_git_stash():
    cmd_push = git_stash_push(message="wip", include_untracked=True)
    assert cmd_push.argv == [
        "git",
        "-C",
        ".",
        "stash",
        "push",
        "-m",
        "wip",
        "--include-untracked",
    ]

    cmd_pop = git_stash_pop(index=1)
    assert cmd_pop.argv == ["git", "-C", ".", "stash", "pop", "stash@{1}"]

    cmd_list = git_stash_list()
    assert cmd_list.argv == ["git", "-C", ".", "stash", "list"]


def test_git_tag():
    # list
    cmd_list = git_tag()
    assert cmd_list.argv == ["git", "-C", ".", "tag", "--list"]

    # create simple
    cmd_create = git_tag(name="v1.0")
    assert cmd_create.argv == ["git", "-C", ".", "tag", "v1.0"]

    # create annotated
    cmd_annotated = git_tag(name="v1.0", message="Release", ref="HEAD~1")
    assert cmd_annotated.argv == [
        "git",
        "-C",
        ".",
        "tag",
        "-a",
        "v1.0",
        "-m",
        "Release",
        "HEAD~1",
    ]

    with pytest.raises(ValueError):
        git_tag(name="-f")

    with pytest.raises(ValueError):
        git_tag(name="v1.0", ref="-f")


def test_git_blame():
    cmd1 = git_blame(file="src/main.py", line_start=10, line_end=20)
    assert cmd1.argv == ["git", "-C", ".", "blame", "-L", "10,20", "--", "src/main.py"]

    with pytest.raises(ValueError):
        git_blame(file="")


def test_git_cherry_pick():
    cmd = git_cherry_pick(commit="abc1234", no_commit=True)
    assert cmd.argv == ["git", "-C", ".", "cherry-pick", "--no-commit", "abc1234"]

    with pytest.raises(ValueError):
        git_cherry_pick(commit="")

    with pytest.raises(ValueError):
        git_cherry_pick(commit="-f")


def test_git_revert():
    cmd = git_revert(commit="abc1234", no_commit=True)
    assert cmd.argv == ["git", "-C", ".", "revert", "--no-commit", "abc1234"]

    with pytest.raises(ValueError):
        git_revert(commit="")

    with pytest.raises(ValueError):
        git_revert(commit="-f")


def test_git_remote():
    cmd = git_remote(verbose=True)
    assert cmd.argv == ["git", "-C", ".", "remote", "-v"]


def test_git_merge():
    cmd = git_merge(branch="feature", no_ff=True, message="Merge feature")
    assert cmd.argv == [
        "git",
        "-C",
        ".",
        "merge",
        "--no-ff",
        "-m",
        "Merge feature",
        "feature",
    ]

    with pytest.raises(ValueError):
        git_merge(branch="")

    with pytest.raises(ValueError):
        git_merge(branch="-f")
