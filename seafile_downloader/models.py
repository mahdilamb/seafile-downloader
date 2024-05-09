"""Module containing models and APIs used throughout the package."""

import datetime
from typing import NamedTuple, TypedDict


class Dirent(TypedDict):
    """A directory entry."""

    size: int
    last_modified: datetime.datetime
    is_dir: bool


class File(Dirent):
    """A file."""

    file_path: str
    file_name: str


class Folder(Dirent):
    """A folder."""

    folder_path: str
    folder_name: str


class SeafileShareLink(NamedTuple):
    """The url information required between steps."""

    domain: str
    link: str
