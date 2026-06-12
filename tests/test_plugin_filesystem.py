"""Tests for mcpipe.plugins.filesystem."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from mcpipe.plugins.filesystem import (
    _fmt_mode,
    _fmt_size,
    _fmt_time,
    fs_cp,
    fs_find,
    fs_grep,
    fs_ls,
    fs_mkdir,
    fs_mv,
    fs_read,
    fs_rm,
    fs_roots,
    fs_stat,
    fs_write,
)


@pytest.fixture(autouse=True)
def fs_sandbox(tmp_path, monkeypatch):
    """Set the allowed filesystem roots to tmp_path."""
    from mcpipe.config import get_config

    cfg = get_config()
    orig_allowed = cfg.paths.allowed
    cfg.paths.allowed = [tmp_path]

    yield tmp_path

    cfg.paths.allowed = orig_allowed


def test_format_helpers():
    assert _fmt_size(500) == "500 B"
    assert _fmt_size(1500) == "1.5 KB"
    assert _fmt_size(1024 * 1024 * 3) == "3.0 MB"
    assert _fmt_size(1024 * 1024 * 1024 * 2) == "2.0 GB"
    assert _fmt_size(1024 * 1024 * 1024 * 1024 * 4) == "4.0 TB"
    assert _fmt_size(1024 * 1024 * 1024 * 1024 * 1024 * 5) == "5.0 PB"

    # Timezone-independent timestamp check
    formatted_time = _fmt_time(0)
    assert formatted_time.startswith("1970-01-01")

    assert "r" in _fmt_mode(0o755)


def test_fs_roots(fs_sandbox):
    assert fs_roots() == str(fs_sandbox.resolve())


def test_fs_write_and_read(fs_sandbox):
    file_path = str(fs_sandbox / "test.txt")
    # Write (new)
    res = fs_write(file_path, "hello world")
    assert "Wrote 11 chars" in res
    assert (fs_sandbox / "test.txt").read_text() == "hello world"

    # Read
    content = fs_read(file_path)
    assert content == "hello world"

    # Write (append)
    fs_write(file_path, " appended", append=True)
    assert fs_read(file_path) == "hello world appended"

    # Read with limit and offset
    assert fs_read(file_path, offset=0, limit=0) == "hello world appended"

    # Read with offset
    assert (
        fs_read(file_path, offset=1) == ""
    )  # Since we split lines, and there's only 1 line

    # Read with limit on multi-line file
    fs_write(file_path, "line1\nline2\nline3\n")
    assert fs_read(file_path, limit=2) == "line1\nline2\n"

    # File not found
    with pytest.raises(FileNotFoundError):
        fs_read(str(fs_sandbox / "nonexistent.txt"))


def test_fs_ls(fs_sandbox):
    sandbox_dir = str(fs_sandbox)
    # Empty directory
    assert fs_ls(sandbox_dir) == "(empty directory)"

    # With files
    fs_write(str(fs_sandbox / "a.txt"), "content")
    fs_write(str(fs_sandbox / "b.txt"), "content")
    fs_write(str(fs_sandbox / ".hidden.txt"), "hidden")

    ls_normal = fs_ls(sandbox_dir)
    assert "a.txt" in ls_normal
    assert "b.txt" in ls_normal
    assert ".hidden.txt" not in ls_normal

    ls_all = fs_ls(sandbox_dir, all=True)
    assert ".hidden.txt" in ls_all

    # Long listing
    ls_long = fs_ls(sandbox_dir, long=True)
    assert "a.txt" in ls_long
    assert "r" in ls_long

    # Long listing OS error fallback
    import inspect

    orig_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        if self.name == "a.txt":
            # Avoid breaking is_dir check during initial sort
            cur_frame = inspect.currentframe()
            try:
                caller = (
                    cur_frame.f_back.f_code.co_name
                    if cur_frame and cur_frame.f_back
                    else ""
                )
                if caller != "is_dir":
                    raise OSError()
            finally:
                del cur_frame
        return orig_stat(self, *args, **kwargs)

    with patch("pathlib.Path.stat", mock_stat):
        ls_error = fs_ls(sandbox_dir, long=True)
        assert "??????????" in ls_error

    with pytest.raises(NotADirectoryError):
        fs_ls(str(fs_sandbox / "a.txt"))


def test_fs_stat(fs_sandbox):
    file_path = str(fs_sandbox / "a.txt")
    fs_write(file_path, "content")
    metadata = fs_stat(file_path)
    assert "type: file" in metadata
    assert "size: 7 B" in metadata

    with pytest.raises(FileNotFoundError):
        fs_stat(str(fs_sandbox / "missing.txt"))


def test_fs_mkdir(fs_sandbox):
    dir_path = str(fs_sandbox / "subdir/nested")
    res = fs_mkdir(dir_path)
    assert "Created" in res
    assert (fs_sandbox / "subdir/nested").is_dir()


def test_fs_rm(fs_sandbox):
    # Delete missing
    with pytest.raises(FileNotFoundError):
        fs_rm(str(fs_sandbox / "missing"))

    # Delete file
    file_path = str(fs_sandbox / "a.txt")
    fs_write(file_path, "content")
    fs_rm(file_path)
    assert not (fs_sandbox / "a.txt").exists()

    # Delete empty dir
    dir_path = str(fs_sandbox / "emptydir")
    fs_mkdir(dir_path)
    fs_rm(dir_path)
    assert not (fs_sandbox / "emptydir").exists()

    # Delete recursive dir
    nested_path = str(fs_sandbox / "nested")
    fs_mkdir(nested_path)
    fs_mkdir(str(fs_sandbox / "nested/dir"))
    fs_write(str(fs_sandbox / "nested/dir/file.txt"), "data")
    fs_rm(nested_path, recursive=True)
    assert not (fs_sandbox / "nested").exists()

    # Delete non-recursive non-empty dir
    nonempty_path = str(fs_sandbox / "nonempty")
    fs_mkdir(nonempty_path)
    fs_write(str(fs_sandbox / "nonempty/f.txt"), "x")
    with pytest.raises(OSError):
        fs_rm(nonempty_path, recursive=False)


def test_fs_mv(fs_sandbox):
    src = str(fs_sandbox / "src.txt")
    dst = str(fs_sandbox / "dst.txt")
    fs_write(src, "data")

    with pytest.raises(FileNotFoundError):
        fs_mv(str(fs_sandbox / "missing.txt"), dst)

    fs_mv(src, dst)
    assert not (fs_sandbox / "src.txt").exists()
    assert (fs_sandbox / "dst.txt").read_text() == "data"


def test_fs_cp(fs_sandbox):
    src = str(fs_sandbox / "src.txt")
    dst = str(fs_sandbox / "dst.txt")

    # Copy missing
    with pytest.raises(FileNotFoundError):
        fs_cp(str(fs_sandbox / "missing.txt"), dst)

    # Copy file
    fs_write(src, "data")
    fs_cp(src, dst)
    assert (fs_sandbox / "src.txt").exists()
    assert (fs_sandbox / "dst.txt").read_text() == "data"

    # Copy dir non-recursive error
    src_dir = str(fs_sandbox / "src_dir")
    dst_dir = str(fs_sandbox / "dst_dir")
    fs_mkdir(src_dir)
    with pytest.raises(IsADirectoryError):
        fs_cp(src_dir, dst_dir)

    # Copy dir recursive
    fs_write(str(fs_sandbox / "src_dir/file.txt"), "nested data")
    fs_cp(src_dir, dst_dir, recursive=True)
    assert (fs_sandbox / "dst_dir/file.txt").read_text() == "nested data"


def test_fs_find(fs_sandbox):
    sandbox_dir = str(fs_sandbox)
    # Setup files
    fs_mkdir(str(fs_sandbox / "subdir"))
    fs_write(str(fs_sandbox / "a.py"), "code")
    fs_write(str(fs_sandbox / "subdir/b.json"), "{}")

    # Not a dir
    with pytest.raises(NotADirectoryError):
        fs_find(str(fs_sandbox / "a.py"))

    # Find files only (with wildcard to trigger dir filtering out)
    res_f = fs_find(sandbox_dir, pattern="*", type="f")
    files = res_f.splitlines()
    assert "a.py" in files
    assert "subdir" not in files

    # Find dirs only
    res_d = fs_find(sandbox_dir, pattern="*", type="d")
    assert "subdir" in res_d
    assert "a.py" not in res_d

    # Find all with max depth
    res_depth = fs_find(sandbox_dir, max_depth=1)
    assert "subdir" in res_depth
    assert "b.json" not in res_depth

    # Find no matches
    assert fs_find(sandbox_dir, pattern="*.java") == "(no matches)"

    # Test allowed root validation exception handling inside glob loop
    import mcpipe.plugins.filesystem as filesystem_mod

    orig_resolve = filesystem_mod._resolve

    def mock_res(path):
        if "b.json" in path:
            raise ValueError("outside allowed roots")
        return orig_resolve(path)

    with patch("mcpipe.plugins.filesystem._resolve", mock_res):
        res_filtered = fs_find(sandbox_dir, pattern="**/*")
        assert "b.json" not in res_filtered

    # Test relative_to ValueError handling
    orig_relative_to = Path.relative_to

    def mock_relative_to(self, *args, **kwargs):
        if "subdir" in self.parts or "a.py" in self.parts:
            raise ValueError("Cannot compute relative path")
        return orig_relative_to(self, *args, **kwargs)

    with patch("pathlib.Path.relative_to", mock_relative_to):
        res_rel_err = fs_find(sandbox_dir, max_depth=1)
        assert res_rel_err == "(no matches)"


def test_fs_grep(fs_sandbox):
    sandbox_dir = str(fs_sandbox)
    cmd = fs_grep(
        pattern="my-pattern",
        path=sandbox_dir,
        include="*.py",
        recursive=True,
        ignore_case=True,
        max_count=5,
    )
    assert cmd.argv == [
        "env",
        "grep",
        "--color=never",
        "-n",
        "-H",
        "-r",
        "-i",
        "-m",
        "5",
        "--include",
        "*.py",
        "my-pattern",
        fs_sandbox.resolve().as_posix(),
    ]


def test_fs_grep_context(fs_sandbox):
    sandbox_dir = str(fs_sandbox)
    cmd = fs_grep(
        pattern="my-pattern",
        path=sandbox_dir,
        before=1,
        after=2,
        context=3,
        recursive=False,
    )
    assert cmd.argv[0] == "bash"
    assert cmd.argv[1] == "-c"

    # Verify the shell script contains the pipefail, the args, and the sed replacement
    script = cmd.argv[2]
    assert script.startswith("set -o pipefail;")
    assert "env grep --color=never -n -H -B 1 -A 2 -C 3 my-pattern" in script
    assert "sed 's/^\\([^:]*\\)-\\([0-9][0-9]*\\)-/\\1:\\2:/'" in script
