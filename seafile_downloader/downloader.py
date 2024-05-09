"""Main module containing the downloader."""

import concurrent.futures
import logging
import os
from collections.abc import Generator, Sequence

import httpx
import tqdm

from seafile_downloader import constants, models, urls

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


def download_file(
    dest: str,
    path: str,
    link: models.SeafileShareLink,
    timeout: int = constants.DEFAULT_TIMEOUT_S,
    retry: int = 3,
    ignore_error: bool = False,
) -> None:
    """Download a file."""
    path = path.lstrip(r"\/")
    dest_file = os.path.join(dest, path)

    with httpx.Client(headers={"Accept": "*/*", "Connection": "keep-alive"}) as client:
        url = f"https://{link.domain}d/{link.link}/files/?p=/{path}&dl=1"
        logger.info(f'GET "{url}"')
        try_count = 0
        while try_count <= retry:
            try_count += 1
            try:
                response = client.get(url, timeout=timeout)
                while response.status_code == 302:
                    response = client.get(
                        response.headers["location"],
                        headers={"Accept": response.headers["content-type"]},
                        timeout=timeout,
                    )
                total = int(response.headers.get("Content-Length", 0)) or None
            except Exception as e:
                if try_count >= retry:
                    if ignore_error:
                        return
                    raise e
                logger.exception(e)

        try_count = 0
        while try_count <= retry:
            try_count += 1
            try:
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                with open(dest_file, "w+b") as w_fp:
                    with tqdm.tqdm(
                        total=total,
                        unit_scale=True,
                        unit_divisor=1024,
                        unit="B",
                        desc=f"Downloading {path}",
                        leave=False,
                    ) as progress:
                        num_bytes_downloaded = response.num_bytes_downloaded
                        for chunk in response.iter_bytes():
                            w_fp.write(chunk)
                            progress.update(
                                response.num_bytes_downloaded - num_bytes_downloaded
                            )
                            num_bytes_downloaded = response.num_bytes_downloaded
                        print(f"Downloaded {path}")
            except Exception as e:
                os.remove(dest_file)
                if try_count >= retry:
                    if ignore_error:
                        return
                    raise e
                logger.exception(e)


def download(
    dest: str,
    url: str,
    timeout: int = constants.DEFAULT_TIMEOUT_S,
    retry: int = constants.DEFAULT_RETRY,
    max_concurrent: int = constants.DEFAULT_MAX_CONCURRENT,
):
    """Run the downloader.

    Args:
        dest (str): The location to download the files to.
        url (str): The URL to download from.
        timeout (int, optional): The timeout that each download request can max out at.
        retry (int, optional): The number of times to try downloading a file.
    """
    link = urls.extract_link(url)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        for _ in concurrent.futures.as_completed(
            executor.submit(
                download_file,
                dest=dest,
                path=file,
                link=link,
                timeout=timeout,
                retry=retry,
                ignore_error=True,
            )
            for file in (
                file.lstrip(os.path.sep)
                for file in list_all_files(link=link, dest=dest)
            )
            if not os.path.exists(os.path.join(dest, file))
        ):
            ...
