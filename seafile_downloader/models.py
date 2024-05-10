"""Module containing models and APIs used throughout the package."""

import datetime
from typing import NamedTuple, TypedDict


class Dirent(TypedDict, total=True):
    """A directory entry."""

    size: int
    last_modified: datetime.datetime
    is_dir: bool


class File(Dirent, total=True):
    """A file."""

    file_path: str
    file_name: str


class Folder(Dirent, total=True):
    """A folder."""

    folder_path: str
    folder_name: str


class SeafileShareLink(NamedTuple):
    """The url information required between steps."""

    domain: str
    link: str
