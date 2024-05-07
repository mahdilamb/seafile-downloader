import datetime
from collections.abc import Sequence
from typing import NamedTuple

import pydantic


class Dirent(pydantic.BaseModel):
    size: int
    last_modified: datetime.datetime
    is_dir: bool


class File(Dirent):
    file_path: str
    file_name: str
    is_dir: bool = False


class Folder(Dirent):
    folder_path: str
    folder_name: str
    is_dir: bool = True


class DirentList(pydantic.BaseModel):
    dirent_list: Sequence[File | Folder]


class SeafileShareLink(NamedTuple):
    domain: str
    link: str


class DownloadConfig(pydantic.BaseModel):
    src: SeafileShareLink
    dest: str
    paths: Sequence[str] | None = None
