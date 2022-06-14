""" Contains progress bar utilities. """

import sys
import signal
import termios
from array import array
from fcntl import ioctl

from .log import logger


def handle_resize(signum, frame):
    h, w = array("h", ioctl(sys.stdout, termios.TIOCGWINSZ, "\0" * 8))[:2]
    global term_width
    term_width = w

try:
    handle_resize(None, None)
    signal.signal(signal.SIGWINCH, handle_resize)
except Exception as e:
    logger.error("Error: %s", str(e))
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
