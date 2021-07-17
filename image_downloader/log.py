"""
This script sets up logger.
"""
import os
import sys
import logging
from pathlib import Path

try:
    data = Path(os.environ["XDG_DATA_HOME"]).absolute() / "image_dl"
except KeyError:
    data = Path(os.environ["HOME"]).absolute() / ".local" / "share" / "image_dl"

data.mkdir(parents=True, exist_ok=True)


logger = logging.getLogger("image_dl")
logger.setLevel(logging.INFO)

file_formatter = logging.Formatter(
    "%(asctime)s - %(pathname)s[line:%(lineno)d] - %(funcName)s - %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
file_handler = logging.FileHandler(str(data / "image_dl.log"))
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(file_formatter)

stream_formatter = logging.Formatter("%(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(stream_formatter)


logger.addHandler(file_handler)
logger.addHandler(stream_handler)
