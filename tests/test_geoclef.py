"""Test downloader for GeoClef."""

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


@pytest.fixture
def test_file_list(geoclef_link):
    """Test that files can be listed."""
    assert len(
        downloader.list_files(geoclef_link, path="/")
    ), "Expected to be able to list files."


if __name__ == "__main__":
    pytest.main([__file__])
