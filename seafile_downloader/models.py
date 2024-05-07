"""Module containing models and APIs used throughout the package."""

import abc
import datetime
from collections.abc import Sequence
from typing import NamedTuple

import pydantic


class Dirent(abc.ABC,pydantic.BaseModel):
    """A directory entry."""

    size: int
    last_modified: datetime.datetime
    is_dir: bool


class File(Dirent):
    """A file."""

    file_path: str
    file_name: str
    is_dir: bool = False


class Folder(Dirent):
    """A folder."""

    folder_path: str
    folder_name: str
    is_dir: bool = True


class DirentList(pydantic.BaseModel):
    """A list of dirents."""

    dirent_list: Sequence[File | Folder]


class SeafileShareLink(NamedTuple):
    """The url information required between steps."""

    domain: str
    link: str


class DownloadConfig(pydantic.BaseModel):
    """Configuration for a download job."""

    src: SeafileShareLink
    dest: str
    paths: Sequence[str] | None = None

