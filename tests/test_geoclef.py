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
        downloader.download_file(
            os.path.join(tmp_dir, "README.MD"),
            path=path,
            link=geoclef_link,
            timeout=5,
        )
        assert os.path.exists(
            os.path.join(tmp_dir, "README.MD")
        ), f"Expected to be able to download {path}."


if __name__ == "__main__":
    pytest.main([__file__])
