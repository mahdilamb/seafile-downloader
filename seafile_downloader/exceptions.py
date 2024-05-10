"""Module containing the exceptions."""


class NoDownloadLinkFoundError(FileNotFoundError):
    """Exception for when a url could not be found to download from."""

    def __init__(self, path: str) -> None:
        """Create an exception when no download link has been found."""
        super().__init__(f"Could not find download link for {path}.")


class DownloadFailedError(IOError):
    """Exception for when a download has failed."""

    def __init__(self, src: str, dest: str) -> None:
        """Create an exception when a download has failed."""
        super().__init__(f"Failed to download {src} to {dest}.")
