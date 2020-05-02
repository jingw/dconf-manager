#!/usr/bin/env python3
import argparse
import configparser
import posixpath
import subprocess

from typing import Dict
from typing import Generic
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import TypeVar
from typing import cast

IGNORED = "\033[38;5;244m? "
REMOVE = "\033[31m< "
ADD = "\033[32m> "


def format_kv(section: str, option: str, value: str) -> str:
    return posixpath.join(section, option) + "=" + value


T = TypeVar("T")


class HierarchicalSet(Generic[T]):
    """A set of paths [a, b, c, ...]

    The root is represented by [].

    Adding a path X causes all paths starting with X to be part of the set.
    For example, adding "a" causes "a/b" to be a member.
    However, adding "a/b" does not cause "a" to be a member.
    """

    def __init__(self) -> None:
        """Create an empty set"""
        self._children: Optional[Dict[T, HierarchicalSet[T]]] = {}
        # Map from child to HierarchicalSet.
        # If empty, this set is empty.
        # If None, this set contains all children.

    def _add(self, path: Sequence[T], i: int) -> None:
        if self._children is not None:
            if i < len(path):
                if path[i] not in self._children:
                    self._children[path[i]] = HierarchicalSet()
                self._children[path[i]]._add(path, i + 1)
            else:
                # we have everything under here
                self._children = None

    def add(self, path: Sequence[T]) -> None:
        self._add(path, 0)

    def __contains__(self, path: Sequence[T], i: int = 0) -> bool:
        """Check if everything in the given path is in this set

        Empty list means to check if the entirety of this node is in the set
        """
        if self._children is None:
            return True
        elif i < len(path):
            if path[i] in self._children:
                return self._children[path[i]].__contains__(path, i + 1)
            else:
                return False
        else:
            return self._children is None

    def _expand_tree(self) -> Sequence[Tuple[int, Optional[T]]]:
        if self._children is None:
            return [(0, None)]
        else:
            result: List[Tuple[int, Optional[T]]] = []
            for k, v in sorted(self._children.items()):
                result.append((0, k))
                for level, item in v._expand_tree():
                    result.append((1 + level, item))
            return result

    def __str__(self) -> str:
        parts = []
        for level, item in self._expand_tree():
            if item is None:
                parts.append("  " * level + "*")
            else:
                parts.append("  " * level + str(item))
        return "\n".join(parts)


def dconf_dump(root: str) -> str:
    output: bytes = subprocess.check_output(["dconf", "dump", root])
    return output.decode()


def dconf_write(key: str, value: str) -> None:
    subprocess.check_call(["dconf", "write", key, value])


def dconf_reset(key: str) -> None:
    subprocess.check_call(["dconf", "reset", key])


class ConfigParser(configparser.ConfigParser):
    def __init__(self) -> None:
        super().__init__(interpolation=None)

    def optionxform(self, optionstr: str) -> str:
        return optionstr


def main(argv: Optional[Sequence[str]]) -> None:
    parser = argparse.ArgumentParser(description="Tool for managing dconf settings",)
    parser.add_argument(
        "-a",
        "--apply",
        default=False,
        action="store_true",
        help="if not passed, only show a diff",
    )
    parser.add_argument("config", type=open, nargs="+", help="INI files to load")
    parser.add_argument(
        "--root", default="/", help="all actions will be relative to this root"
    )
    parser.add_argument(
        "-i",
        "--show-ignored",
        default=False,
        action="store_true",
        help="if true, print unmanaged options",
    )
    args = parser.parse_args(argv)

    root = args.root
    dconf_output = dconf_dump(root)
    dconf_config = ConfigParser()
    dconf_config.read_string(dconf_output)

    def write(section: str, option: str, value: str, apply: bool) -> None:
        key = posixpath.join(root, section, option)
        print(ADD + format_kv(section, option, value))
        if apply:
            dconf_write(key, value)

    def reset(section: str, option: str, value: str, apply: bool) -> None:
        key = posixpath.join(root, section, option)
        print(REMOVE + format_kv(section, option, value))
        if apply:
            dconf_reset(key)

    desired_config = ConfigParser()
    for f in args.config:
        desired_config.read_file(f)

    # excluded sections override managed sections
    managed_sections = HierarchicalSet[str]()
    excluded_sections = HierarchicalSet[str]()
    for section in desired_config:
        if section.startswith("-"):
            excluded_sections.add(section[1:].split("/"))
        else:
            managed_sections.add(section.split("/"))

    sections_union = sorted(
        set(dconf_config.keys())
        | set(k for k in desired_config.keys() if not k.startswith("-"))
    )

    for section in sections_union:
        section_parts = section.split("/")
        if section_parts in excluded_sections or section_parts not in managed_sections:
            # Section is not managed at all.
            if args.show_ignored:
                for option, value in dconf_config[section].items():
                    print(IGNORED + format_kv(section, option, value))
        elif section not in dconf_config:
            # Adding a new section.
            for option, value in desired_config[section].items():
                write(section, option, value, args.apply)
        else:
            # Section is present and managed, so diff at option level.
            dconf_section = dconf_config[section]
            # But it might be managed at a higher level, so it might not be in desired_config.
            # In that case we'll end up resetting everything.
            desired_section = (
                desired_config[section]
                if section in desired_config
                else cast(Mapping[str, str], {})
            )
            for option in sorted(
                set(dconf_section.keys()) | set(desired_section.keys())
            ):
                if option not in dconf_section:
                    write(section, option, desired_section[option], args.apply)
                elif option not in desired_section:
                    reset(section, option, dconf_section[option], args.apply)
                elif dconf_section[option] != desired_section[option]:
                    reset(section, option, dconf_section[option], False)
                    write(section, option, desired_section[option], args.apply)
                else:
                    # option is equal, do nothing
                    pass


if __name__ == "__main__":
    main(None)
