"""CLI entry point for SeaFile downloader."""

import argparse
from collections.abc import Sequence

from seafile_downloader import downloader


def create_parser() -> argparse.ArgumentParser:
    """Create the parser for CLI entry."""
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--out", default=".")
    return parser


def main(args: Sequence[str] | None = None) -> None:
    """Run the downloader from the CLI args."""
    values = vars(create_parser().parse_args(args))
    downloader.download(url=values["url"], dest=values["out"])


if __name__ == "__main__":
    main()
