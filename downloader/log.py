"""
This script sets up logger.
"""
import os
import logging
from pathlib import Path

try:
    data = Path(os.environ["XDG_DATA_HOME"]) / "resource_dl"
except KeyError:
    data = Path(os.environ["HOME"]) / ".local" / "share" / "resource_dl"

data.mkdir(parents=True, exist_ok=True)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Log to file
file_formatter = logging.Formatter(
    "%(asctime)s - %(pathname)s[line:%(lineno)d] - %(funcName)s - %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
file_handler = logging.FileHandler(str(data / "resource_dl.log"), mode="w")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

# Log to stderr
stream_formatter = logging.Formatter("%(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(stream_formatter)
stream_handler.setLevel(logging.DEBUG)


logger.addHandler(file_handler)
logger.addHandler(stream_handler)
