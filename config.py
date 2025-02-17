from os.path import join
from pathlib import Path

# Base API configuration
BASE_URL = "https://cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/"
QURAN_PAGES = join(BASE_URL, "editions/{}/pages/{}.json")
QURAN_INFO = join(BASE_URL, "info.json")

# Available Quran editions
QURAN_EDITIONS = [
    "ara-quransimple",
    "ara-quranuthmanienc",
    "ara-quranuthmanihaf",
    "ara-quranuthmanihaf1"
]

# JSON formatting
INDENT_SIZE = 2

# Default paths
DATA_DIR = Path("quran_data")
DB_DIR = Path("databases")

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

# Database configuration
DB_PRAGMAS = [
    "PRAGMA foreign_keys = ON",
    "PRAGMA synchronous = OFF",
    "PRAGMA journal_mode = MEMORY",
    "PRAGMA cache_size = 10000"
]

# Default concurrency settings
DEFAULT_BATCH_SIZE = 50
DEFAULT_MAX_CONCURRENT = 8