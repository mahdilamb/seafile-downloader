"""Test downloader for GeoClef."""

import os
import tempfile

import pytest

from seafile_downloader import downloader, models, urls


@pytest.fixture(scope="session")
def geoclef_url() -> str:
    """Get the url for GeoClef."""
    return "https://lab.plantnet.org/seafile/d/bdb829337aa44a9489f6/"


@pytest.fixture(scope="session")
def geoclef_link(geoclef_url) -> models.SeafileShareLink:
    """Get the Seafile sharelink for GeoClef."""
    return urls.extract_link(geoclef_url)


def test_file_list(geoclef_link):
    """Test that files can be listed."""
    assert len(
        downloader.list_files(geoclef_link, path="/")
    ), "Expected to be able to list files."


def test_recursive_file_list(
    geoclef_link, path: str = "/EnvironmentalRasters/HumanFootprint/"
):
    """Test that the recursive method of listing files works."""
    assert any(
        os.path.sep in os.path.relpath(file_path, path)
        for file_path in downloader.list_all_files(geoclef_link, path=path)
    )


def test_file_download(
    geoclef_link, path: str = "/EnvironmentalRasters/HumanFootprint/HF_README.txt"
):
    """Test downloading a file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        downloader.download_file(tmp_dir, path=path, link=geoclef_link, timeout=5)
        assert os.path.exists(
            os.path.join(tmp_dir, path.lstrip(r"\/"))
        ), f"Expected to be able to download {path}."


@pytest.mark.parametrize(("retry",), [(0,), (3,)])
def test_failed_file_download_empty(
    geoclef_link,
    mock_client_factory,
    retry: int,
    path: str = "/EnvironmentalRasters/HumanFootprint/HF_README.txt",
):
    """Test that files that fail download are removed."""
    try_count = 0

    class ErrorResponse:
        status_code = 200
        headers = {}
        num_bytes_downloaded = 3

        def iter_bytes(self):
            nonlocal try_count
            for i in range(3):
                yield str(i).encode()
                self.num_bytes_downloaded -= 1
            try_count += 1
            raise Exception()

    with (
        tempfile.TemporaryDirectory() as tmp_dir,
        mock_client_factory(ErrorResponse()),
    ):
        with pytest.raises(Exception) as _:
            downloader.download_file(
                tmp_dir, path=path, link=geoclef_link, timeout=5, retry=retry
            )
        assert not os.path.exists(
            os.path.join(tmp_dir, path.lstrip(r"\/"))
        ), "Expected the failed download to be deleted."
        assert try_count >= 1 and try_count <= max(
            1, retry
        ), f"Expected number of retries to be at least once, and at most retry {retry}."


if __name__ == "__main__":
    pytest.main([__file__])
