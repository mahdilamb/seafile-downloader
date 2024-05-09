"""Constants used throughout the package."""

import os

SEAFILE_API_VERSION = "v2.1"
DEFAULT_TIMEOUT_S: int = 600
DEFAULT_RETRY: int = 3
DEFAULT_MAX_CONCURRENT = os.cpu_count() or 8
