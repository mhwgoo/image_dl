import pathlib
import argparse
import re
from urllib.parse import urlparse


def parse_args():
    """Get the arguments from command line"""
    parser = argparse.ArgumentParser(
        description="Download images from one or multiple urls"
    )
    parser.add_argument("url", help="A url to download from")
    parser.add_argument("-d", "--dir", help="Directory to save images")
    parser.add_argument(
        "--formats",
        nargs="*",
        default=["jpg", "png", "gif", "svg", "jpeg", "webp"],
        help="Specify formats in a list without any separator",
    )

    args = parser.parse_args()
    return args


def get_url(args):
    url = args.url
    if re.match(r"^[a-zA-z]+://", url):
        return url
    else:
        return "https://" + url


def get_download_dir(url, dir_name):
    if dir_name:
        dl_dir = pathlib.Path(dir_name + f"_{urlparse(url).netloc}")
    else:
        dl_dir = pathlib.Path() / f"images_{urlparse(url).netloc}"
    return dl_dir
