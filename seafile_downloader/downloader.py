"""Main module containing the downloader."""

import asyncio
import logging
import os
from collections.abc import Sequence

import httpx
import tqdm
import tqdm.asyncio

from seafile_downloader import constants, models, urls

logger = logging.getLogger()


async def alist_files(
    link: models.SeafileShareLink,
    path: str = "/",
):
    """List the files from seafile share link."""
    url = f"https://{link.domain}api/{constants.SEAFILE_API_VERSION}/share-links/{link.link}/dirents/?&path={path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise Exception(response.text)
        return models.DirentList.model_validate_json(response.text).dirent_list


async def alist_all_files(
    link: models.SeafileShareLink, path: str = "/"
) -> Sequence[str]:
    """List all the files recursively."""
    files: Sequence[str] = []
    for dirent in await alist_files(link, path=path):
        if isinstance(dirent, models.Folder):
            files.extend(await alist_all_files(link, path=dirent.folder_path))
        else:
            files.append(dirent.file_path)
    return tuple(files)


async def adownload_file(
    dest: str,
    path: str,
    link: models.SeafileShareLink,
    timeout: int = constants.DEFAULT_TIMEOUT_S,
) -> None:
    """Download a file asynchronously."""
    path = path.lstrip(r"\/")
    dest_file = os.path.join(dest, path)
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)

    async with httpx.AsyncClient(
        headers={"Accept": "*/*", "Connection": "keep-alive"}
    ) as client:
        url = f"https://{link.domain}d/{link.link}/files/?p=/{path}&dl=1"
        logger.info(f'GET "{url}"')
        response = await client.get(url, timeout=timeout)
        while response.status_code == 302:
            response = await client.get(
                response.headers["location"],
                headers={"Accept": response.headers["content-type"]},
                timeout=timeout,
            )
        total = int(response.headers.get("Content-Length", 0)) or None
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
            os.remove(dest_file)
            raise e


async def adownload_all(dest: str, url: str, timeout: int):
    """Await the download for all files."""
    link = urls.extract_link(url)
    config = models.DownloadConfig(src=link, dest=dest)
    config_path = os.path.join(dest, f".seafile-downloader-config-{link.link}.json")
    if not os.path.exists(config_path):
        logger.info(f"Storing config to {config_path}.")
        os.makedirs(dest, exist_ok=True)
        with open(config_path, "w") as fp:
            fp.write(config.model_dump_json())
    else:
        logger.info(f"Loading config from {config_path}.")
        with open(config_path) as fp:
            config = models.DownloadConfig.model_validate_json(fp.read())
    if config.paths is None:
        logger.info("Downloading file list...")
        config.paths = await alist_all_files(link=config.src)
        with open(config_path, "w") as fp:
            fp.write(config.model_dump_json())
        logger.info("...done")
    if config.paths:
        for task in tqdm.asyncio.tqdm.as_completed(
            [
                adownload_file(dest, file, link=config.src, timeout=timeout)
                for file in (file.lstrip(os.path.sep) for file in config.paths)
                if not os.path.exists(os.path.join(dest, file))
            ]
        ):
            await task


def download(dest: str, url: str, timeout: int = constants.DEFAULT_TIMEOUT_S):
    """Run the async downloader.

    Args:
        dest (str): The location to download the files to.
        url (str): The URL to download from.
        timeout (int, optional): The timeout that each download request can max out at.F
    """
    asyncio.run(adownload_all(dest, url, timeout))
