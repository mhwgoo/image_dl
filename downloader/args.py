""" Contains arg parser and progress bar utilities. """

import sys
import re
import pathlib
import argparse
from urllib.parse import urlparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download image and html files from one or multiple urls"
    )

    # Add positional argument url 
    parser.add_argument(
        "url",
        help="a url to download from",
    )
    parser.add_argument("-d", "--dir", help="name given for creating a new directory in current folder")

    # Add sub-command capability that can identify different sub-command names
    sub_parsers = parser.add_subparsers(dest='subparser_name')

    # Add sub-command image 
    parser_image = sub_parsers.add_parser("image", help="download images on the web page")
    # Add optional argument format
    parser_image.add_argument(
        "--format",
        nargs="*",
        default=["jpg", "png", "gif", "svg", "jpeg", "webp"],
        help="seperate multiple image format with space",
    )

    # Add sub-command html 
    parser_html = sub_parsers.add_parser("html", help="download html files")
    # Add optional argument level
    parser_html.add_argument(
        "--level",
        default = 1,
        help="levels of html page to download from, defaults to 1",
    )

    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    return args


def get_url(url):
    if re.match(r"^[a-zA-z]+://", url):
        return url
    else:
        return "https://" + url


def get_download_dir(url, dir_name):
    if dir_name:
        dir = pathlib.Path(dir_name)  # dir.absolute(): PosixPath("current folder path/dir_name")
    else:
        dir = pathlib.Path(urlparse(url).netloc)
    return dir
