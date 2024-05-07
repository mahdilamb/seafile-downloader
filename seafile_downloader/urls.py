"""Utilit functions for working with URLs."""

import re

from seafile_downloader import models

URL_PATTERN = re.compile(r"https?:\/\/(.*?\/.*?seafile.*?\/)d\/([A-Za-z0-9]{2,})")


def extract_link(url: str) -> models.SeafileShareLink:
    """Collect the SeafileLink from a URL."""
    return models.SeafileShareLink(*next(URL_PATTERN.finditer(url)).groups())
