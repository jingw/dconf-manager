from __future__ import annotations

import io
import os
import subprocess
import textwrap
import unittest
from typing import Sequence
from unittest import mock

from dconf_manager import HierarchicalSet
from dconf_manager import main

EXPECTED_OUTPUT = """\
\033[32m> add/AddedKey=1
\033[31m< clear/foo/bar/blah=50
\033[31m< overwrite/a=1
\033[32m> overwrite/a=10
\033[31m< overwrite/b=2
\033[32m> overwrite/new=5
"""
EXPECTED_OUTPUT_WITH_IGNORED = """\
\033[32m> add/AddedKey=1
\033[38;5;244m? clear/keep=5
\033[31m< clear/foo/bar/blah=50
\033[38;5;244m? clear/foo/bar/exclude/no=1
\033[38;5;244m? clear/food/hi=1
\033[38;5;244m? ignored/a=1
\033[31m< overwrite/a=1
\033[32m> overwrite/a=10
\033[31m< overwrite/b=2
\033[32m> overwrite/new=5
"""


class TestDconfManager(unittest.TestCase):
    def test_hierarchical_set(self) -> None:
        s = HierarchicalSet[int]()
        assert str(s) == ""
        assert [] not in s
        assert [0] not in s

        s.add([1, 2, 3])
        assert str(s) == textwrap.dedent(
            """\
        1
          2
            3
              *"""
        )
        s.add([1, 2, 3, 4])
        assert str(s) == textwrap.dedent(
            """\
        1
          2
            3
              *"""
        )
        assert [] not in s
        assert [0] not in s
        assert [1] not in s
        assert [1, 2] not in s
        assert [1, 2, 3] in s
        assert [1, 2, 3, 3] in s
        assert (1, 2, 3, 4) in s

        s.add((1, 2))
        assert str(s) == textwrap.dedent(
            """\
        1
          2
            *"""
        )
        assert [] not in s
        assert [0] not in s
        assert [1] not in s
        assert [1, 2] in s
        assert [1, 2, 3] in s
        assert [1, 2, 3, 3] in s
        assert (1, 2, 3, 4) in s

        s.add([2])
        assert str(s) == textwrap.dedent(
            """\
        1
          2
            *
        2
          *"""
        )
        assert [] not in s
        assert [0] not in s
        assert [1] not in s
        assert [2] in s
        assert [2, 5] in s

        s.add([])
        assert str(s) == "*"
        assert [] in s
        assert [0] in s
        assert [1] in s
        assert [5, 6, 7, 8] in s

    @mock.patch("dconf_manager.dconf_dump")
    @mock.patch("dconf_manager.dconf_write")
    @mock.patch("dconf_manager.dconf_reset")
    def _test_main(
        self,
        apply: bool,
        show_ignored: bool,
        reset: mock.Mock,
        write: mock.Mock,
        dump: mock.Mock,
    ) -> tuple[Sequence[tuple[object, ...]], Sequence[tuple[object, ...]], str]:
        config = textwrap.dedent(
            """\
        [ignored]
        a=1
        [overwrite]
        a=1
        b=2
        [clear]
        keep=5
        [clear/foo/bar]
        blah=50
        [clear/foo/bar/exclude]
        no=1
        [clear/food]
        hi=1
        """
        )
        dump.return_value = config
        input = os.path.join(os.path.dirname(__file__), "test-data", "input.ini")
        stdout = io.StringIO()
        args = [input, "--root", "/the/root"]
        if show_ignored:
            args.append("--show-ignored")
        if apply:
            args.append("--apply")
        with mock.patch("sys.stdout", stdout):
            main(args)
        dump.assert_called_once_with("/the/root")

        return write.call_args_list, reset.call_args_list, stdout.getvalue()

    def test_diff(self) -> None:
        writes, resets, stdout = self._test_main(False, False)
        assert not writes
        assert not resets
        assert stdout == EXPECTED_OUTPUT

    def test_diff_with_ignored(self) -> None:
        writes, resets, stdout = self._test_main(False, True)
        assert not writes
        assert not resets
        assert stdout == EXPECTED_OUTPUT_WITH_IGNORED

    def test_apply(self) -> None:
        writes, resets, stdout = self._test_main(True, False)
        assert writes == [
            mock.call("/the/root/add/AddedKey", "1"),
            mock.call("/the/root/overwrite/a", "10"),
            mock.call("/the/root/overwrite/new", "5"),
        ]
        assert resets == [
            mock.call("/the/root/clear/foo/bar/blah"),
            mock.call("/the/root/overwrite/b"),
        ]
        assert stdout == EXPECTED_OUTPUT


class TestTools(unittest.TestCase):
    def test_black(self) -> None:
        subprocess.check_call(["black", "--check", os.path.dirname(__file__)])

    def test_flake8(self) -> None:
        subprocess.check_call(["flake8"], cwd=os.path.dirname(__file__))

    def test_isort(self) -> None:
        subprocess.check_call(
            ["isort", "--check-only", "--diff", os.path.dirname(__file__)]
        )

    def test_mypy(self) -> None:
        subprocess.check_call(["mypy", os.path.dirname(__file__)])
