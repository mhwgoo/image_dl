""" Contains arg parser and progress bar utilities. """

import sys
import re
import time
import pathlib
import argparse
import signal
import termios
from urllib.parse import urlparse
from array import array
from fcntl import ioctl

from log import logger

# ---terminal arguments---#
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
        help="Seperate multiple format strings with space",
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


# ---Progress Bar---#
def handle_resize(signum, frame):
    h, w = array("h", ioctl(sys.stdout, termios.TIOCGWINSZ, "\0" * 8))[:2]
    global term_width
    term_width = w


try:
    handle_resize(None, None)
    signal.signal(signal.SIGWINCH, handle_resize)
except:
    logger.error("Error: %s", e.message)
    term_width = 79


def get_bar(percentage, bar_width):
    marker = "|"
    curr_width = int(bar_width * percentage / 100)
    bar = (marker * curr_width).ljust(bar_width)
    return bar


def update(curr_val, max_val):
    assert 0 <= curr_val <= max_val
    percent = curr_val * 100 / max_val
    percent_str = "%3d%%" % (percent)
    bar_width = term_width - len(percent_str) - len(" ")
    bar = get_bar(percent, bar_width)
    print("\r" + percent_str + " " + bar, end="", flush=True)
