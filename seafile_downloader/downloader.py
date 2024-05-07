import asyncio
import os
import re
from collections.abc import Generator

import httpx
import tqdm
import tqdm.asyncio

from seafile_downloader import constants, models

URL_PATTERN = re.compile(r"https?:\/\/(.*?\/.*?seafile.*?\/)d\/([A-Za-z0-9]{2,})")


def list_files(
    link: models.SeafileShareLink, path: str, client: httpx.Client | None = None
):
    if client is None:
        client = httpx.Client()
    url = f"https://{link.domain}api/{constants.SEAFILE_API_VERSION}/share-links/{link.link}/dirents/?&path={path}"
    with client:
        response = client.get(url, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise Exception(response.text)
        return models.DirentList.model_validate_json(response.text).dirent_list


def iter_files(
    dest: str, link: models.SeafileShareLink, path: str = "/"
) -> Generator[str, None, None]:
    for dirent in list_files(link, path=path):
        if dirent.is_dir:
            yield from iter_files(dest, link, path=dirent.folder_path)
        else:
            yield dirent.file_path


async def download_file(
    dest: str, path: str, link: models.SeafileShareLink, timeout: int = 600
) -> None:
    dest_file = os.path.join(dest, path)
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)

    async with httpx.AsyncClient(
        headers={"Accept": "*/*", "Connection": "keep-alive"}, timeout=timeout
    ) as client:
        response = await client.get(
            f"https://{link.domain}d/{link.link}/files/?&p=/{path}&dl=1",
        )
        if response.status_code == 302:
            response = await client.get(
                response.headers["location"],
                headers={"Accept": response.headers["content-type"]},
                timeout=timeout,
            )
        total = int(response.headers.get("Content-Length", 0))
        if total:
            try:
                with open(dest_file, "w+b") as w_fp:
                    with tqdm.tqdm(
                        total=total,
                        unit_scale=True,
                        unit_divisor=1024,
                        unit="B",
                        leave=False,
                    ) as progress:
                        num_bytes_downloaded = response.num_bytes_downloaded
                        for chunk in response.iter_bytes():
                            w_fp.write(chunk)
                            progress.update(
                                response.num_bytes_downloaded - num_bytes_downloaded
                            )
                            num_bytes_downloaded = response.num_bytes_downloaded
            except Exception as e:
                os.unlink(dest_file)
                raise e


async def download_all(dest: str, url: str):
    """Await the download for all files."""
    link = models.SeafileShareLink(*next(URL_PATTERN.finditer(url)).groups())
    config = models.DownloadConfig(src=link, dest=dest)
    config_path = os.path.join(dest, f".seafile-downloader-config-{link.link}.json")
    if not os.path.exists(config_path):
        os.makedirs(dest, exist_ok=True)
        with open(config_path, "w") as fp:
            fp.write(config.model_dump_json())
    else:
        with open(config_path) as fp:
            config = models.DownloadConfig.model_validate_json(fp.read())
    if config.paths is None:
        config.paths = tuple(iter_files(dest, link=config.src))
        with open(config_path, "w") as fp:
            fp.write(config.model_dump_json())
    if config.paths:
        for task in tqdm.asyncio.tqdm.as_completed(
            [
                download_file(dest, file, link=config.src)
                for file in (file.lstrip(os.path.sep) for file in config.paths)
                if not os.path.exists(os.path.join(dest, file))
            ]
        ):
            await task


def download(dest: str, url: str):
    """Run the async downloader.

    Args:
        url (str): The URL to download from.
    """
    asyncio.run(download_all(dest, url))
