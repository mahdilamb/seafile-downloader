"""Main module containing the downloader."""

import concurrent.futures
import functools
import logging
import os
from collections.abc import Generator, Mapping, Sequence
from typing import Any

import backoff
import httpx
import tqdm

from seafile_downloader import constants, exceptions, models, urls

logger = logging.getLogger()


def list_files(
    link: models.SeafileShareLink,
    path: str = "/",
):
    """List the files from seafile share link."""
    url = f"https://{link.domain}api/{constants.SEAFILE_API_VERSION}/share-links/{link.link}/dirents/?&path={path}"
    with httpx.Client() as client:
        response = client.get(url, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise Exception(response.text)
        data: Sequence[models.Dirent] = response.json()["dirent_list"]
        return tuple(
            (models.Folder if dirent["is_dir"] else models.File)(**dirent)
            for dirent in data
        )


def list_all_files(
    link: models.SeafileShareLink,
    path: str = "/",
    dest: str | None = None,
) -> Generator[str, None, None]:
    """List all the files recursively."""
    for dirent in list_files(link, path=path):
        if dirent["is_dir"]:
            if dest:
                os.makedirs(os.path.join(dest, path.lstrip(os.path.sep)), exist_ok=True)
            yield from list_all_files(link, path=dirent["folder_path"], dest=dest)
        else:
            yield dirent["file_path"]


@functools.cache
def find_link(
    path: str,
    link: models.SeafileShareLink,
    timeout: int = constants.DEFAULT_TIMEOUT_S,
):
    """Get the HTTP response containing the download information."""
    path = path.lstrip(r"\/")
    with httpx.Client(headers={"Accept": "*/*", "Connection": "keep-alive"}) as client:
        url = f"https://{link.domain}d/{link.link}/files/?p=/{path}&dl=1"
        logger.info(f'GET "{url}"')
        try:
            response = client.get(url, timeout=timeout)
            while response.status_code == 302:
                response = client.get(
                    response.headers["location"],
                    headers={"Accept": response.headers["content-type"]},
                    timeout=timeout,
                )
        except Exception as e:
            raise FileNotFoundError(path) from e
    return response


def download_file(
    dest: str,
    path: str,
    link: models.SeafileShareLink,
    timeout: int = constants.DEFAULT_TIMEOUT_S,
    tqdm_kwargs: Mapping[str, Any] = None,  # type: ignore
) -> str:
    """Download a file."""
    if os.path.exists(dest):
        return dest
    path = path.lstrip(r"\/")
    response = find_link(path=path, link=link, timeout=timeout)
    total = int(response.headers.get("Content-Length", 0)) or None
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w+b") as w_fp:
            with tqdm.tqdm(
                total=total,
                unit_scale=True,
                unit_divisor=1024,
                unit="B",
                desc=path,
                **(tqdm_kwargs or {}),
            ) as progress:
                num_bytes_downloaded = response.num_bytes_downloaded
                for chunk in response.iter_bytes():
                    w_fp.write(chunk)
                    progress.update(
                        response.num_bytes_downloaded - num_bytes_downloaded
                    )
                    num_bytes_downloaded = response.num_bytes_downloaded
    except Exception as e:
        if os.path.exists(dest):
            os.remove(dest)
        raise exceptions.DownloadFailedError(path, dest) from e
    return dest


def download(
    dest: str,
    url: str,
    timeout: int = constants.DEFAULT_TIMEOUT_S,
    retry: int = constants.DEFAULT_RETRY,
    max_concurrent: int | None = constants.DEFAULT_MAX_CONCURRENT,
):
    """Run the downloader.

    Args:
        dest (str): The location to download the files to.
        url (str): The URL to download from.
        timeout (int, optional): The timeout that each download request can max out at.
        retry (int, optional): The number of times to try downloading a file.
        max_concurrent (int, optional): The maximum number of concurrent downloads.
    """
    link = urls.extract_link(url)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        for future in concurrent.futures.as_completed(
            executor.submit(
                backoff.on_exception(
                    backoff.expo,
                    (
                        exceptions.DownloadFailedError,
                        exceptions.NoDownloadLinkFoundError,
                    ),
                    max_tries=retry,
                )(download_file),
                dest=os.path.join(dest, file.lstrip(os.path.sep)),
                path=file,
                link=link,
                timeout=timeout,
                tqdm_kwargs={"position": i, "leave": False},
            )
            for i, file in enumerate(
                file.lstrip(os.path.sep)
                for file in list_all_files(link=link, dest=dest)
            )
        ):
            try:
                dest_path = future.result()
                print(f"Downloaded {dest_path}.")
            except Exception as exc:
                logger.exception(exc)
