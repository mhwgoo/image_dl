""" Contains arg parser and progress bar utilities. """

import sys
import re
import pathlib
import argparse
from urllib.parse import urlparse, unquote


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download images. Save html files to markdown formats."
    )

    # Add sub-command capability that can identify different sub-command names
    sub_parsers = parser.add_subparsers(dest='subparser_name')

    # Add sub-command image 
    parser_image = sub_parsers.add_parser("image", help="download images on the web page")
    # Add positional argument url 
    parser_image.add_argument(
        "url",
        help="a url to download from",
    )

    # Add optional argument format
    parser_image.add_argument(
        "-f",
        "--format",
        nargs="*",
        default=["jpg", "png", "gif", "svg", "jpeg", "webp"],
        help="seperate multiple image format with space",
    )
    parser_image.add_argument(
        "--width",
        type=int,
        default=-1,
        help="height of the image"
    )
    parser_image.add_argument(
        "--height",
        type=int,
        default=-1,
        help="width of the image"
    )
 
    # Add optional argument dir
    parser_image.add_argument(
            "-d", 
            "--dir", 
            help="name given for creating a new directory in current folder"
    )

    # Add sub-command html 
    parser_html = sub_parsers.add_parser("html", help="save one html file or files from links on the web page to markdown formats")
    # Add positional argument url 
    parser_html.add_argument(
        "url",
        help="a url to download from",
    )
    # Add optional argument level
    parser_html.add_argument(
        "--level",
        default = 1,
        help="defaults to 1 for saving the current page; can be set 2 for crawling links on the current page",
    )
    # Add optional argument dir
    parser_html.add_argument(
            "-d", 
            "--dir", 
            help="name given for creating a new directory in current folder"
    )

    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(0)

    if sys.argv[1] == "image" and len(sys.argv) == 2:
        parser_image.print_help()
        sys.exit(0)

    if sys.argv[1] == "html" and len(sys.argv) == 2:
        parser_html.print_help()
        sys.exit(0)

    args = parser.parse_args()
    return args


def get_url(url):
    if re.match(r"^[a-zA-z]+://", url):
        return unquote(url) 
    else:
        return unquote("https://" + url)


def get_download_dir(url, dir_name):
    if dir_name:
        dir = pathlib.Path(dir_name)  # dir.absolute(): PosixPath("current folder path/dir_name")
        return (True, dir)
    else:
        dir = pathlib.Path(urlparse(url).netloc)
        return (False, dir) 
