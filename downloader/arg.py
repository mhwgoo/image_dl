""" Contains arg parser and progress bar utilities. """

import re
import pathlib
import argparse
from urllib.parse import urlparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download resources including files and images from one or multiple urls"
    )
    parser.add_argument("url", help="A url or multiple urls to download from")
    parser.add_argument("-d", "--dir", help="Directory to save resources")
    parser.add_argument(
        "--format",
        nargs="*",
        # default=["jpg", "png", "gif", "svg", "jpeg", "webp"],
        help="Seperate multiple format strings with space",
    )

    args = parser.parse_args()
    return args


def get_url(url):
    if re.match(r"^[a-zA-z]+://", url):
        return url
    else:
        return "https://" + url


def get_download_dir(url, dir_name):
    if dir_name:
        dl_dir = pathlib.Path(dir_name + f"_{urlparse(url).netloc}")
    else:
        dl_dir = pathlib.Path() / urlparse(url).netloc
    return dl_dir


