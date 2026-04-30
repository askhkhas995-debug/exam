"""Tests for shell_validators module."""
from __future__ import annotations

import os
import stat
import tarfile
import tempfile
from pathlib import Path

import pytest

from piscine_forge.evaluators.shell_validators import (
    validate_file_content,
    validate_hardlink,
    validate_permissions,
    validate_symlink,
    validate_tar_archive,
    validate_tar_member_properties,
    validate_timestamp,
    validate_weird_filename,
)


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory(prefix="pforge-test-") as d:
        yield Path(d)


# ---------------------------------------------------------------------------
# Tar archive
# ---------------------------------------------------------------------------

class TestTarArchive:
    def test_valid_tar(self, tmpdir):
        inner = tmpdir / "hello.txt"
        inner.write_text("hello\n")
        archive = tmpdir / "test.tar"
        with tarfile.open(archive, "w") as tf:
            tf.add(inner, arcname="hello.txt")
        ok, detail = validate_tar_archive(archive, expected_contents=["hello.txt"])
        assert ok, detail

    def test_missing_entry(self, tmpdir):
        inner = tmpdir / "hello.txt"
        inner.write_text("hello\n")
        archive = tmpdir / "test.tar"
        with tarfile.open(archive, "w") as tf:
            tf.add(inner, arcname="hello.txt")
        ok, detail = validate_tar_archive(archive, expected_contents=["missing.txt"])
        assert not ok
        assert "missing" in detail

    def test_forbidden_entry(self, tmpdir):
        inner = tmpdir / "secret.txt"
        inner.write_text("secret\n")
        archive = tmpdir / "test.tar"
        with tarfile.open(archive, "w") as tf:
            tf.add(inner, arcname="secret.txt")
        ok, detail = validate_tar_archive(archive, forbidden_contents=["secret.txt"])
        assert not ok
        assert "forbidden" in detail

    def test_missing_archive(self, tmpdir):
        ok, detail = validate_tar_archive(tmpdir / "nonexistent.tar")
        assert not ok
        assert "not found" in detail

    def test_invalid_archive(self, tmpdir):
        bad = tmpdir / "bad.tar"
        bad.write_text("not a tar file")
        ok, detail = validate_tar_archive(bad)
        assert not ok
        assert "invalid" in detail


class TestTarMember:
    def test_symlink_member(self, tmpdir):
        archive = tmpdir / "test.tar"
        with tarfile.open(archive, "w") as tf:
            info = tarfile.TarInfo(name="link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/bin/sh"
            tf.addfile(info)
        ok, detail = validate_tar_member_properties(
            archive, "link", is_symlink=True, expected_linkname="/bin/sh"
        )
        assert ok, detail

    def test_wrong_linkname(self, tmpdir):
        archive = tmpdir / "test.tar"
        with tarfile.open(archive, "w") as tf:
            info = tarfile.TarInfo(name="link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/bin/bash"
            tf.addfile(info)
        ok, detail = validate_tar_member_properties(
            archive, "link", expected_linkname="/bin/sh"
        )
        assert not ok


# ---------------------------------------------------------------------------
# Symlink
# ---------------------------------------------------------------------------

class TestSymlink:
    def test_valid_symlink(self, tmpdir):
        target = tmpdir / "target.txt"
        target.write_text("target\n")
        link = tmpdir / "link.txt"
        link.symlink_to(target)
        ok, detail = validate_symlink(link)
        assert ok, detail

    def test_not_a_symlink(self, tmpdir):
        regular = tmpdir / "regular.txt"
        regular.write_text("regular\n")
        ok, detail = validate_symlink(regular)
        assert not ok
        assert "not a symbolic link" in detail

    def test_symlink_target(self, tmpdir):
        target = tmpdir / "target.txt"
        target.write_text("target\n")
        link = tmpdir / "link.txt"
        link.symlink_to(target)
        ok, detail = validate_symlink(link, expected_target=str(target))
        assert ok, detail

    def test_wrong_target(self, tmpdir):
        target = tmpdir / "target.txt"
        target.write_text("target\n")
        link = tmpdir / "link.txt"
        link.symlink_to(target)
        ok, detail = validate_symlink(link, expected_target="/bin/sh")
        assert not ok


# ---------------------------------------------------------------------------
# Hardlink
# ---------------------------------------------------------------------------

class TestHardlink:
    def test_valid_hardlink(self, tmpdir):
        original = tmpdir / "original.txt"
        original.write_text("data\n")
        hardlink = tmpdir / "hardlink.txt"
        os.link(original, hardlink)
        ok, detail = validate_hardlink(original, hardlink)
        assert ok, detail
        assert "inode" in detail

    def test_not_hardlinked(self, tmpdir):
        f1 = tmpdir / "f1.txt"
        f1.write_text("data\n")
        f2 = tmpdir / "f2.txt"
        f2.write_text("data\n")
        ok, detail = validate_hardlink(f1, f2)
        assert not ok
        assert "not hardlinked" in detail


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class TestPermissions:
    def test_correct_permissions(self, tmpdir):
        f = tmpdir / "script.sh"
        f.write_text("#!/bin/sh\n")
        os.chmod(f, 0o755)
        ok, detail = validate_permissions(f, 0o755)
        assert ok, detail

    def test_wrong_permissions(self, tmpdir):
        f = tmpdir / "script.sh"
        f.write_text("#!/bin/sh\n")
        os.chmod(f, 0o644)
        ok, detail = validate_permissions(f, 0o755)
        assert not ok
        assert "0o644" in detail


# ---------------------------------------------------------------------------
# Timestamp
# ---------------------------------------------------------------------------

class TestTimestamp:
    def test_current_timestamp(self, tmpdir):
        f = tmpdir / "file.txt"
        f.write_text("data\n")
        ok, detail = validate_timestamp(f, expected_timestamp=os.stat(f).st_mtime)
        assert ok, detail


# ---------------------------------------------------------------------------
# Weird filenames
# ---------------------------------------------------------------------------

class TestWeirdFilename:
    def test_normal_filename(self, tmpdir):
        (tmpdir / "normal.txt").write_text("data\n")
        ok, detail = validate_weird_filename(tmpdir, "normal.txt")
        assert ok, detail

    def test_filename_with_spaces(self, tmpdir):
        (tmpdir / "my file.txt").write_text("data\n")
        ok, detail = validate_weird_filename(tmpdir, "my file.txt")
        assert ok, detail

    def test_filename_with_special_chars(self, tmpdir):
        name = "test$file"
        (tmpdir / name).write_text("data\n")
        ok, detail = validate_weird_filename(tmpdir, name)
        assert ok, detail

    def test_missing_weird_filename(self, tmpdir):
        ok, detail = validate_weird_filename(tmpdir, "nonexistent$file")
        assert not ok


# ---------------------------------------------------------------------------
# File content
# ---------------------------------------------------------------------------

class TestFileContent:
    def test_exact_content(self, tmpdir):
        f = tmpdir / "test.txt"
        f.write_text("hello world\n")
        ok, detail = validate_file_content(f, expected_content="hello world\n")
        assert ok, detail

    def test_contains(self, tmpdir):
        f = tmpdir / "test.txt"
        f.write_text("ssh-rsa AAAA... user@host\n")
        ok, detail = validate_file_content(f, contains=["ssh-"])
        assert ok, detail

    def test_missing_content(self, tmpdir):
        f = tmpdir / "test.txt"
        f.write_text("no key here\n")
        ok, detail = validate_file_content(f, contains=["ssh-"])
        assert not ok
